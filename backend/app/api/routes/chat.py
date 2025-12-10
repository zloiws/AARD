"""
Chat API routes with streaming and cancellation support
"""
from typing import Optional, List, Dict
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncio
import json
import uuid
import time
from datetime import datetime

from app.core.ollama_client import get_ollama_client, OllamaClient, TaskType, OllamaError
from app.core.templates import templates
from app.core.chat_session import get_session_manager, ChatSessionManager
from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_current_trace_id
from app.core.execution_context import ExecutionContext
from app.core.request_orchestrator import RequestOrchestrator
from app.services.request_logger import RequestLogger
from app.services.prompt_service import PromptService
from app.models.prompt import PromptType
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = LoggingConfig.get_logger(__name__)

# Store active generation tasks for cancellation
_active_tasks: dict[str, asyncio.Task] = {}
_current_generation_task: Optional[asyncio.Task] = None
_current_generation_id: Optional[str] = None
_cancellation_event: Optional[asyncio.Event] = None


def _extract_plan_results(plan) -> str:
    """
    Извлечь результаты выполнения плана для ответа пользователю
    
    Args:
        plan: Выполненный план
        
    Returns:
        Текстовое представление результатов
    """
    import json
    
    if not plan:
        return "План не найден"
    
    # Получить шаги плана
    steps = plan.steps if hasattr(plan, 'steps') else []
    if isinstance(steps, str):
        try:
            steps = json.loads(steps)
        except:
            steps = []
    
    results = []
    
    for i, step in enumerate(steps):
        step_result = step.get("result")
        step_output = step.get("output")
        step_status = step.get("status", "unknown")
        
        # Приоритет: output > result > status
        if step_output:
            results.append(f"Шаг {i+1}: {step_output}")
        elif step_result:
            if isinstance(step_result, dict):
                result_text = step_result.get("output") or step_result.get("result") or str(step_result)
            else:
                result_text = str(step_result)
            
            if result_text and result_text != "None":
                results.append(f"Шаг {i+1}: {result_text}")
    
    # Если есть результаты шагов
    if results:
        return "\n\n".join(results)
    
    # Если план завершен, но результатов нет - возвращаем статус
    if plan.status == "completed":
        return f"План выполнен успешно. Выполнено шагов: {len(steps)}"
    
    # Если план не завершен
    return f"План в процессе выполнения. Статус: {plan.status}"


class ChatMessage(BaseModel):
    """Chat message model"""
    message: str = Field(..., description="User message")
    task_type: Optional[str] = Field(
        default="general_chat",
        description="Type of task (code_generation, reasoning, general_chat, etc.)"
    )
    model: Optional[str] = Field(
        default=None,
        description="Specific model to use (overrides task_type selection)"
    )
    server_id: Optional[str] = Field(
        default=None,
        description="Ollama server ID from database (required when model is specified)"
    )
    temperature: Optional[float] = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for generation"
    )
    stream: bool = Field(default=False, description="Stream response")
    session_id: Optional[str] = Field(default=None, description="Chat session ID")
    system_prompt: Optional[str] = Field(default=None, description="System prompt for the model")


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str
    model: str
    task_type: str
    duration_ms: Optional[int] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    reasoning: Optional[str] = None  # Reasoning/thinking text if model supports it
    workflow_id: Optional[str] = None  # Workflow ID for tracking execution timeline


class MultiModelChatRequest(BaseModel):
    """Request for multi-model chat (models talking to each other)"""
    models: List[str] = Field(..., description="List of model names to participate")
    initial_message: str = Field(..., description="Initial message to start conversation")
    system_prompts: Dict[str, str] = Field(default_factory=dict, description="System prompts for each model")
    max_turns: int = Field(default=10, ge=1, le=50, description="Maximum conversation turns")
    session_id: Optional[str] = Field(default=None, description="Chat session ID")


@router.post("/")
async def chat(
    request: Request,
    chat_message: ChatMessage,
    client: OllamaClient = Depends(get_ollama_client),
    session_manager: ChatSessionManager = Depends(get_session_manager),
    db: Session = Depends(get_db)
):
    """
    Send message to chat and get response from LLM
    
    Selects appropriate model based on task_type:
    - code_generation / code_analysis: uses coding model (qwen3-coder)
    - reasoning / planning: uses reasoning model (deepseek-r1)
    - general_chat: uses general model (deepseek-r1)
    
    If system_prompt is not provided, tries to fetch active system prompt from database.
    """
    try:
        # Get or create session
        session_id = chat_message.session_id
        if not session_id:
            # Create new session
            session = session_manager.create_session(
                db,
                system_prompt=chat_message.system_prompt,
                title=chat_message.message[:100] if chat_message.message else None
            )
            session_id = session.id
        else:
            # Get existing session
            session = session_manager.get_session(db, session_id)
            if not session:
                # Session not found, create new one
                session = session_manager.create_session(
                    db,
                    system_prompt=chat_message.system_prompt,
                    title=chat_message.message[:100] if chat_message.message else None
                )
                session_id = session.id
        
        # Add user message to session
        session_manager.add_message(
            db,
            session_id,
            "user",
            chat_message.message,
            metadata={"task_type": chat_message.task_type}
        )
        
        # Get system prompt - try database first, then use provided or session default
        system_prompt = chat_message.system_prompt
        if not system_prompt:
            # Try to get active system prompt from database
            try:
                prompt_service = PromptService(db)
                db_prompt = prompt_service.get_active_prompt(
                    prompt_type=PromptType.SYSTEM,
                    level=0
                )
                if db_prompt:
                    system_prompt = db_prompt.prompt_text
                    logger.debug(f"Using system prompt from database: {db_prompt.name}")
            except Exception as e:
                logger.warning(f"Failed to fetch system prompt from database: {e}")
        
        # Use session system_prompt if available and no override
        if not system_prompt and session and session.system_prompt:
            system_prompt = session.system_prompt
        
        # Initialize workflow tracker
        from app.core.workflow_tracker import get_workflow_tracker, WorkflowStage
        workflow_tracker = get_workflow_tracker()
        workflow_id = str(uuid.uuid4())
        
        # Start workflow tracking
        username = "user"  # TODO: Get from auth context when available
        workflow_tracker.start_workflow(workflow_id, chat_message.message, username=username, interaction_type="chat")
        
        # Save initial workflow events to DB
        from app.services.workflow_event_service import WorkflowEventService
        from app.models.workflow_event import EventSource, EventType, EventStatus, WorkflowStage as DBWorkflowStage
        from app.core.tracing import get_current_trace_id
        
        event_service = WorkflowEventService(db)
        trace_id = get_current_trace_id()
        
        # Save user input event
        try:
            event_service.save_event(
                workflow_id=workflow_id,
                event_type=EventType.USER_INPUT,
                event_source=EventSource.USER,
                stage=DBWorkflowStage.USER_REQUEST,
                message=f"Запрос пользователя: {chat_message.message[:200]}",
                event_data={"message": chat_message.message, "task_type": chat_message.task_type},
                metadata={"username": username, "interaction_type": "chat"},
                session_id=session_id,
                trace_id=trace_id
            )
        except Exception as e:
            logger.warning(f"Failed to save workflow event to DB: {e}", exc_info=True)
        
        # Track user request
        workflow_tracker.add_event(
            WorkflowStage.USER_REQUEST,
            f"Получен запрос: {chat_message.message[:100]}"
        )
        
        # Determine request type
        try:
            task_type = TaskType(chat_message.task_type) if chat_message.task_type else TaskType.DEFAULT
        except ValueError:
            task_type = TaskType.DEFAULT
        
        start_time = time.time()
        
        # Создать ExecutionContext
        context = ExecutionContext.from_request(
            request,
            db=db,
            workflow_id=workflow_id,
            session_id=session_id,
            trace_id=trace_id
        )
        
        # Использовать RequestOrchestrator для обработки запроса
        orchestrator = RequestOrchestrator()
        result = await orchestrator.process_request(
            message=chat_message.message,
            context=context,
            task_type=chat_message.task_type,
            model=chat_message.model,
            server_id=chat_message.server_id,
            temperature=chat_message.temperature
        )
        
        # Добавить ответ в сессию
        session_manager.add_message(
            db,
            session_id,
            "assistant",
            result.response,
            metadata=result.metadata
        )
        
        return ChatResponse(
            response=result.response,
            model=result.model,
            task_type=result.task_type,
            duration_ms=result.duration_ms,
            session_id=session_id,
            trace_id=trace_id,
            workflow_id=workflow_id
        )
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _stream_generation(
    client: OllamaClient,
    prompt: str,
    task_type: TaskType,
    model: str,
    server_url: str,
    temperature: float,
    session_id: str,
    session_manager: ChatSessionManager,
    db: Session
):
    """Stream generation response"""
    try:
        chat_history = session_manager.get_ollama_history(db, session_id)
        async for chunk in client.generate_stream(
            prompt=prompt,
            task_type=task_type,
            model=model,
            server_url=server_url,
            history=chat_history,
            temperature=temperature
        ):
            yield f"data: {json.dumps({'content': chunk.response, 'done': chunk.done})}\n\n"
    except Exception as e:
        logger.error(f"Error in stream generation: {e}", exc_info=True)
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.get("/session/{session_id}")
async def get_chat_session(
    session_id: str,
    session_manager: ChatSessionManager = Depends(get_session_manager),
    db: Session = Depends(get_db)
):
    """Get chat session with all messages"""
    session = session_manager.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.id,
        "created_at": session.created_at.isoformat(),
        "title": session.title,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "model": msg.model,
                "timestamp": msg.timestamp.isoformat(),
                "metadata": msg.metadata
            }
            for msg in session.messages
        ]
    }


@router.post("/session")
async def create_chat_session(
    request: Request,
    title: Optional[str] = None,
    system_prompt: Optional[str] = None,
    session_manager: ChatSessionManager = Depends(get_session_manager),
    db: Session = Depends(get_db)
):
    """Create a new chat session"""
    try:
        # Try to get system prompt from database if not provided
        if not system_prompt:
            try:
                prompt_service = PromptService(db)
                db_prompt = prompt_service.get_active_prompt(
                    prompt_type=PromptType.SYSTEM,
                    level=0
                )
                if db_prompt:
                    system_prompt = db_prompt.prompt_text
                    logger.debug(f"Using system prompt from database: {db_prompt.name}")
            except Exception as e:
                logger.warning(f"Failed to fetch system prompt from database: {e}")
        
        session = session_manager.create_session(
            db,
            system_prompt=system_prompt,
            title=title
        )
        
        return {
            "session_id": session.id,
            "created_at": session.created_at.isoformat(),
            "title": session.title,
            "system_prompt": session.system_prompt
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/session/{session_id}")
async def delete_chat_session(
    session_id: str,
    session_manager: ChatSessionManager = Depends(get_session_manager),
    db: Session = Depends(get_db)
):
    """Delete a chat session and all its messages"""
    try:
        session_manager.delete_session(db, session_id)
        return {"status": "success", "message": f"Session {session_id} deleted"}
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/multi-model")
async def multi_model_chat(
    request: MultiModelChatRequest,
    client: OllamaClient = Depends(get_ollama_client),
    session_manager: ChatSessionManager = Depends(get_session_manager),
    db: Session = Depends(get_db)
):
    """
    Multi-model chat - models talking to each other
    """
    # Implementation for multi-model chat
    # This is a placeholder - full implementation would require coordination logic
    return {"status": "not_implemented", "message": "Multi-model chat coming soon"}
