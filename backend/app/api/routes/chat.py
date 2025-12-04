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
from datetime import datetime

from app.core.ollama_client import get_ollama_client, OllamaClient, TaskType
from app.core.templates import templates
from app.core.chat_session import get_session_manager, ChatSessionManager
from app.core.database import get_db
from app.core.logging_config import LoggingConfig
from app.core.tracing import get_current_trace_id
from app.services.request_logger import RequestLogger
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = LoggingConfig.get_logger(__name__)

# Store active generation tasks for cancellation
_active_tasks: dict[str, asyncio.Task] = {}
_current_generation_task: Optional[asyncio.Task] = None
_current_generation_id: Optional[str] = None
_cancellation_event: Optional[asyncio.Event] = None


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
    """
    import time
    
    try:
        # Initialize workflow tracker
        from app.core.workflow_tracker import get_workflow_tracker, WorkflowStage
        workflow_tracker = get_workflow_tracker()
        workflow_id = str(uuid.uuid4())
        
        # Start workflow tracking
        # Get username from request if available (for now use "user" as default)
        username = "user"  # TODO: Get from auth context when available
        workflow_tracker.start_workflow(workflow_id, chat_message.message, username=username)
        workflow_tracker.add_event(
            WorkflowStage.REQUEST_PARSING,
            f"Разбор запроса, определение действий. Тип задачи: {chat_message.task_type}"
        )
        
        # Log incoming request
        logger.debug(
            "Chat request received",
            extra={
                "message_preview": chat_message.message[:50] if chat_message.message else None,
                "server_id": chat_message.server_id,
                "model": chat_message.model,
                "task_type": chat_message.task_type,
                "stream": chat_message.stream,
                "session_id": chat_message.session_id,
            }
        )
        
        # Get or create session
        session_id = chat_message.session_id
        if not session_id:
            session = session_manager.create_session(
                db=db,
                system_prompt=chat_message.system_prompt,
                title=chat_message.message[:50] if chat_message.message else None
            )
            session_id = session.id
        else:
            session = session_manager.get_session(db, session_id)
            if not session:
                # Try to create new session if old one not found
                session = session_manager.create_session(
                    db=db,
                    system_prompt=chat_message.system_prompt,
                    title=chat_message.message[:50] if chat_message.message else None
                )
                session_id = session.id
        
        # Add user message to session
        session_manager.add_message(db, session_id, "user", chat_message.message)
        
        # Parse task type
        try:
            task_type = TaskType(chat_message.task_type)
        except ValueError:
            task_type = TaskType.DEFAULT
        
        start_time = time.time()
        
        # Generate response
        # IMPORTANT: Always use database, never fallback to .env configuration
        from app.services.ollama_service import OllamaService
        
        selected_model = None
        selected_server_url = None
        selected_server = None
        
        # PRIORITY 1: If server_id is provided, get server from database
        if chat_message.server_id and chat_message.server_id.strip():
            selected_server = OllamaService.get_server_by_id(db, chat_message.server_id.strip())
            if not selected_server:
                raise HTTPException(status_code=404, detail=f"Server {chat_message.server_id} not found")
            selected_server_url = selected_server.get_api_url()
            logger.info(
                "Using specified server",
                extra={
                    "server_id": str(selected_server.id),
                    "server_name": selected_server.name,
                    "server_url": selected_server.url,
                }
            )
        
        # PRIORITY 2: If model is provided, use it
        if chat_message.model and chat_message.model.strip():
            selected_model = chat_message.model.strip()
            logger.debug(
                "Model explicitly selected from request",
                extra={"model": selected_model}
            )
        else:
            logger.debug("No model provided in request, will auto-select")
        
        # PRIORITY 3: Auto-select from database (NOT from .env!)
        if not selected_server_url or not selected_model:
            # Get default server from database
            if not selected_server:
                try:
                    selected_server = OllamaService.get_default_server(db)
                    logger.debug(
                        "Default server lookup",
                        extra={
                            "server_id": str(selected_server.id) if selected_server else None,
                            "server_name": selected_server.name if selected_server else None,
                        }
                    )
                except Exception as e:
                    logger.error(
                        "Failed to get default server",
                        exc_info=True,
                        extra={"error": str(e)}
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Database error while getting default server: {str(e)}"
                    )
                
                if not selected_server:
                    # Fallback to first active server
                    try:
                        servers = OllamaService.get_all_active_servers(db)
                        logger.debug(
                            "Active servers lookup",
                            extra={"count": len(servers) if servers else 0}
                        )
                    except Exception as e:
                        logger.error(
                            "Failed to get active servers",
                            exc_info=True,
                            extra={"error": str(e)}
                        )
                        raise HTTPException(
                            status_code=500,
                            detail=f"Database error while getting active servers: {str(e)}"
                        )
                    
                    if servers:
                        selected_server = servers[0]
                    else:
                        raise HTTPException(
                            status_code=503,
                            detail="No active Ollama servers found in database. Please add a server in Settings."
                        )
                
                try:
                    selected_server_url = selected_server.get_api_url()
                    logger.info(
                        "Auto-selected server",
                        extra={
                            "server_id": str(selected_server.id),
                            "server_name": selected_server.name,
                            "server_url": selected_server.url,
                        }
                    )
                except Exception as e:
                    logger.error(
                        "Failed to get API URL",
                        exc_info=True,
                        extra={
                            "server_id": str(selected_server.id),
                            "error": str(e)
                        }
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error getting server API URL: {str(e)}"
                    )
            
            # If model not selected, get models from database and select based on task_type
            if not selected_model:
                models = OllamaService.get_models_for_server(db, str(selected_server.id))
                if not models:
                    raise HTTPException(
                        status_code=503,
                        detail=f"No models found for server {selected_server.name}. Please sync models in Settings."
                    )
                
                # Select model based on task_type and capabilities
                # For now, just use first active model
                # TODO: Implement smart selection based on task_type and model capabilities
                selected_model = models[0].model_name
                logger.debug(
                    "Auto-selected model",
                    extra={
                        "model": selected_model,
                        "available_models_count": len(models),
                        "available_models": [m.model_name for m in models],
                    }
                )
        
        # Ensure we have both server_url and model
        if not selected_server_url:
            raise HTTPException(status_code=500, detail="Failed to determine server URL")
        if not selected_model:
            raise HTTPException(status_code=500, detail="Failed to determine model")
        
        # Log final selection
        logger.info(
            "Model and server selected",
            extra={
                "server_url": selected_server_url,
                "model": selected_model,
                "task_type": task_type.value,
            }
        )
        
        # Track model selection
        workflow_tracker.add_event(
            WorkflowStage.ACTION_DETERMINATION,
            f"Выбрана модель: {selected_model} на сервере {selected_server.name if selected_server else 'unknown'}",
            details={"model": selected_model, "server": selected_server_url}
        )
        
        # Prepare prompt with system prompt if provided
        prompt = chat_message.message
        if chat_message.system_prompt:
            prompt = f"{chat_message.system_prompt}\n\nUser: {chat_message.message}\nAssistant:"
        
        if chat_message.stream:
            # Stream response
            return StreamingResponse(
                _stream_generation(client, prompt, task_type, selected_model, selected_server_url,
                                 chat_message.temperature, session_id, session_manager, db),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming response
            # Create cancellation event for this request
            global _current_generation_id, _cancellation_event
            generation_id = str(uuid.uuid4())
            _current_generation_id = generation_id
            _cancellation_event = asyncio.Event()
            _active_tasks[generation_id] = asyncio.current_task()
            
            try:
                # Track execution start
                workflow_tracker.add_event(
                    WorkflowStage.EXECUTION,
                    f"Выполняю запрос к модели {selected_model}..."
                )
                
                ollama_response = await client.generate(
                    prompt=prompt,
                    task_type=task_type,
                    model=selected_model,
                    server_url=selected_server_url,
                    system_prompt=chat_message.system_prompt,
                    history=session_manager.get_ollama_history(db, session_id),
                    stream=False,
                    temperature=chat_message.temperature
                )
                
                # Track response received
                workflow_tracker.add_event(
                    WorkflowStage.EXECUTION,
                    f"Получен ответ от модели ({len(ollama_response.response)} символов)"
                )
            except asyncio.CancelledError:
                # Generation was cancelled
                workflow_tracker.add_event(
                    WorkflowStage.ERROR,
                    "Выполнение отменено пользователем"
                )
                session_manager.add_message(
                    db,
                    session_id,
                    "assistant",
                    "\n\n[Генерация отменена пользователем]",
                    metadata={"cancelled": True}
                )
                raise HTTPException(status_code=499, detail="Generation cancelled by user")
            finally:
                # Clean up
                if generation_id in _active_tasks:
                    del _active_tasks[generation_id]
                if _current_generation_id == generation_id:
                    _current_generation_id = None
                    _cancellation_event = None
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log request to request_logs
            try:
                request_logger = RequestLogger(db)
                trace_id = get_current_trace_id()
                request_log = request_logger.log_request(
                    request_type="chat",
                    request_data={
                        "message": chat_message.message[:500],  # Truncate for storage
                        "task_type": task_type.value,
                        "temperature": chat_message.temperature,
                    },
                    status="success",
                    model_used=ollama_response.model,
                    server_url=selected_server_url,
                    response_data={
                        "response_length": len(ollama_response.response),
                        "task_type": task_type.value,
                    },
                    duration_ms=duration_ms,
                    session_id=session_id,
                    trace_id=trace_id,
                )
                logger.debug(
                    "Request logged",
                    extra={"request_log_id": str(request_log.id), "rank": request_log.overall_rank}
                )
            except Exception as e:
                logger.warning(f"Failed to log request: {e}", exc_info=True)
            
            # Add assistant response to session
            session_manager.add_message(
                db,
                session_id, 
                "assistant", 
                ollama_response.response,
                model=ollama_response.model,
                metadata={"duration_ms": duration_ms, "task_type": task_type.value}
            )
            
            # Track response content
            workflow_tracker.add_event(
                WorkflowStage.RESULT,
                f"Ответ модели: {ollama_response.response}",
                details={
                    "model": ollama_response.model,
                    "response_length": len(ollama_response.response),
                    "full_response": ollama_response.response
                }
            )
            
            # Track completion
            workflow_tracker.finish_workflow(
                result=f"Запрос выполнен успешно. Получен ответ длиной {len(ollama_response.response)} символов"
            )
            
            response_data = ChatResponse(
                response=ollama_response.response,
                model=ollama_response.model,
                task_type=task_type.value,
                duration_ms=duration_ms,
                session_id=session_id,
                trace_id=trace_id
            )
            
            # If request is from HTMX, return HTML fragment
            if request and "text/html" in request.headers.get("accept", ""):
                from datetime import datetime
                from fastapi.responses import HTMLResponse
                response = templates.TemplateResponse(
                    "message_fragment.html",
                    {
                        "request": request,
                        "message": ollama_response.response,
                        "model": ollama_response.model,
                        "timestamp": datetime.now(),
                        "duration_ms": duration_ms,
                        "trace_id": trace_id
                    }
                )
                # Add trace_id and session_id to response headers
                if trace_id:
                    response.headers["X-Trace-Id"] = trace_id
                if session_id:
                    response.headers["X-Session-Id"] = session_id
                return response
            
            return response_data
        
    except Exception as e:
        import traceback
        error_msg = f"Error generating response: {str(e)}"
        
        # Track error in workflow
        try:
            from app.core.workflow_tracker import get_workflow_tracker, WorkflowStage
            workflow_tracker = get_workflow_tracker()
            workflow_tracker.add_event(
                WorkflowStage.ERROR,
                f"Ошибка выполнения: {error_msg}"
            )
            workflow_tracker.finish_workflow(error=error_msg)
        except Exception as tracker_error:
            logger.warning(f"Failed to track workflow error: {tracker_error}")
        
        # Log failed request
        try:
            duration_ms = int((time.time() - start_time) * 1000) if 'start_time' in locals() else None
            request_logger = RequestLogger(db)
            trace_id = get_current_trace_id()
            request_log = request_logger.log_request(
                request_type="chat",
                request_data={
                    "message": chat_message.message[:500] if chat_message else None,
                    "task_type": chat_message.task_type if chat_message else None,
                },
                status="failed",
                error_message=str(e)[:1000],
                duration_ms=duration_ms,
                session_id=chat_message.session_id if chat_message else None,
                trace_id=trace_id,
            )
        except Exception as log_error:
            logger.warning(f"Failed to log failed request: {log_error}", exc_info=True)
        
        logger.error(
            "Chat request failed",
            exc_info=True,
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "task_type": chat_message.task_type if chat_message else None,
            }
        )
        
        if request and "text/html" in request.headers.get("accept", ""):
            raise HTTPException(
                status_code=500,
                detail=error_msg,
                headers={"HX-Retarget": "#messages", "HX-Reswap": "beforeend"}
            )
        raise HTTPException(status_code=500, detail=error_msg)


async def _stream_generation(
    client: OllamaClient,
    prompt: str,
    task_type: TaskType,
    model: Optional[str],
    server_url: Optional[str],
    temperature: float,
    session_id: str,
    session_manager: ChatSessionManager,
    db: Session
):
    """Stream generation with cancellation support"""
    full_response = ""
    model_name = None
    
    try:
        # Get session for history
        session = session_manager.get_session(db, session_id)
        history = session_manager.get_ollama_history(db, session_id) if session else []
        system_prompt = session.system_prompt if session else None
        
        async for chunk in client.generate_stream(
            prompt=prompt,
            task_type=task_type,
            model=model,
            server_url=server_url,
            system_prompt=system_prompt,
            history=history,
            temperature=temperature
        ):
            if chunk.response:
                full_response += chunk.response
                model_name = chunk.model
                yield f"data: {json.dumps({'content': chunk.response, 'done': False})}\n\n"
            
            if chunk.done:
                # Add complete message to session
                session_manager.add_message(
                    db,
                    session_id,
                    "assistant",
                    full_response,
                    model=model_name
                )
                yield f"data: {json.dumps({'content': '', 'done': True, 'model': model_name})}\n\n"
                break
    
    except asyncio.CancelledError:
        # Save partial response if cancelled
        if full_response:
            session_manager.add_message(
                db,
                session_id,
                "assistant",
                full_response + "\n\n[Generation cancelled]",
                model=model_name,
                metadata={"cancelled": True}
            )
        yield f"data: {json.dumps({'error': 'Generation cancelled'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/cancel")
async def cancel_generation():
    """Cancel the current active generation task"""
    global _current_generation_task, _current_generation_id, _cancellation_event
    
    if _current_generation_id and _current_generation_id in _active_tasks:
        task = _active_tasks[_current_generation_id]
        task.cancel()
        if _cancellation_event:
            _cancellation_event.set()
        return {"status": "cancelled", "task_id": _current_generation_id}
    
    return {"status": "not_found", "message": "No active generation to cancel"}


@router.post("/multi-model")
async def multi_model_chat(
    request: MultiModelChatRequest,
    client: OllamaClient = Depends(get_ollama_client),
    session_manager: ChatSessionManager = Depends(get_session_manager),
    db: Session = Depends(get_db)
):
    """
    Create a conversation between multiple models
    Each model can have its own system prompt
    """
    if len(request.models) < 2:
        raise HTTPException(status_code=400, detail="At least 2 models required for multi-model chat")
    
    # Create or get session
    session_id = request.session_id
    if not session_id:
        session = session_manager.create_session(db=db, title="Multi-model conversation")
        session_id = session.id
    
    # Initialize conversation
    current_message = request.initial_message
    conversation = []
    session_manager.add_message(db, session_id, "system", f"Multi-model conversation started with models: {', '.join(request.models)}")
    session_manager.add_message(db, session_id, "user", current_message)
    
    # Run conversation
    for turn in range(request.max_turns):
        model_idx = turn % len(request.models)
        model_name = request.models[model_idx]
        system_prompt = request.system_prompts.get(model_name, "")
        
        # Prepare prompt
        prompt = current_message
        if system_prompt:
            prompt = f"{system_prompt}\n\nUser: {current_message}\nAssistant:"
        
        try:
            # Generate response
            response = await client.generate(
                prompt=prompt,
                model=model_name,
                task_type=TaskType.GENERAL_CHAT,
                temperature=0.7
            )
            
            response_text = response.response
            
            # Add to conversation
            conversation.append({
                "turn": turn + 1,
                "model": model_name,
                "message": response_text
            })
            
            session_manager.add_message(
                db,
                session_id,
                "assistant",
                response_text,
                model=model_name,
                metadata={"turn": turn + 1, "multi_model": True}
            )
            
            # Next model responds to this message
            current_message = response_text
        
        except Exception as e:
            conversation.append({
                "turn": turn + 1,
                "model": model_name,
                "error": str(e)
            })
            break
    
    return {
        "session_id": session_id,
        "conversation": conversation,
        "turns": len(conversation)
    }


@router.get("/models")
async def list_models(client: OllamaClient = Depends(get_ollama_client)):
    """List available Ollama models"""
    models = []
    for instance in client.instances:
        models.append({
            "model": instance.model,
            "url": instance.url,
            "capabilities": instance.capabilities,
            "max_concurrent": instance.max_concurrent
        })
    return {"models": models}


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    session_manager: ChatSessionManager = Depends(get_session_manager),
    db: Session = Depends(get_db)
):
    """Get chat session with history"""
    session = session_manager.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.id,
        "created_at": session.created_at.isoformat() if isinstance(session.created_at, datetime) else session.created_at,
        "title": session.title,
        "messages": [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "model": msg.model,
                "timestamp": msg.timestamp.isoformat() if isinstance(msg.timestamp, datetime) else msg.timestamp,
                "metadata": msg.metadata
            }
            for msg in session.messages
        ]
    }


@router.post("/session")
async def create_session(
    system_prompt: Optional[str] = None,
    title: Optional[str] = None,
    session_manager: ChatSessionManager = Depends(get_session_manager),
    db: Session = Depends(get_db)
):
    """Create a new chat session"""
    session = session_manager.create_session(db=db, system_prompt=system_prompt, title=title)
    return {
        "session_id": session.id,
        "created_at": session.created_at.isoformat() if isinstance(session.created_at, datetime) else session.created_at,
        "title": session.title
    }
