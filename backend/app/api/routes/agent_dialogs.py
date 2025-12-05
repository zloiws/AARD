"""
API routes for agent dialogs/conversations
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.agent_dialog_service import AgentDialogService
from app.services.agent_service import AgentService
from app.models.agent_conversation import AgentConversation, ConversationStatus, MessageRole
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)
router = APIRouter(prefix="/api/agent-dialogs", tags=["agent-dialogs"])


# Request/Response models
class ConversationCreate(BaseModel):
    """Request model for creating a conversation"""
    participant_ids: List[UUID] = Field(..., description="List of agent IDs participating in the conversation", min_items=2)
    goal: Optional[str] = Field(None, description="Goal of the conversation")
    title: Optional[str] = Field(None, description="Optional title for the conversation")
    description: Optional[str] = Field(None, description="Optional description")
    task_id: Optional[UUID] = Field(None, description="Optional link to a task")
    initial_context: Optional[Dict[str, Any]] = Field(None, description="Optional initial context")


class MessageAdd(BaseModel):
    """Request model for adding a message to conversation"""
    agent_id: UUID = Field(..., description="Agent ID sending the message")
    content: str = Field(..., description="Message content")
    role: Optional[str] = Field(MessageRole.AGENT.value, description="Message role (agent, system, user)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional message metadata")


class MessageSend(BaseModel):
    """Request model for sending message with A2A notifications"""
    sender_agent_id: UUID = Field(..., description="Agent ID sending the message")
    content: str = Field(..., description="Message content")
    recipient_agent_ids: Optional[List[UUID]] = Field(None, description="Optional list of specific recipients (if None, sends to all other participants)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional message metadata")


class ContextUpdate(BaseModel):
    """Request model for updating conversation context"""
    updates: Dict[str, Any] = Field(..., description="Dictionary with context updates")


class ConversationResponse(BaseModel):
    """Response model for conversation"""
    id: str
    task_id: Optional[str]
    participants: List[str]
    messages: List[Dict[str, Any]]
    context: Dict[str, Any]
    goal: Optional[str]
    status: str
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Response model for message"""
    id: str
    agent_id: str
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    conversation_data: ConversationCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new conversation between agents
    
    Requires at least 2 participants. All participants must be active agents.
    """
    try:
        dialog_service = AgentDialogService(db)
        
        conversation = dialog_service.create_conversation(
            participant_ids=conversation_data.participant_ids,
            goal=conversation_data.goal,
            title=conversation_data.title,
            description=conversation_data.description,
            task_id=conversation_data.task_id,
            initial_context=conversation_data.initial_context
        )
        
        return conversation.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db)
):
    """Get conversation by ID"""
    dialog_service = AgentDialogService(db)
    conversation = dialog_service.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    
    return conversation.to_dict()


@router.get("/", response_model=List[ConversationResponse])
async def list_conversations(
    task_id: Optional[UUID] = Query(None, description="Filter by task ID"),
    agent_id: Optional[UUID] = Query(None, description="Filter by agent ID (participant)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    List conversations with optional filters
    
    Can filter by task_id, agent_id (participant), or status
    """
    dialog_service = AgentDialogService(db)
    
    if task_id:
        conversations = dialog_service.get_conversations_by_task(task_id)
    elif agent_id:
        conversations = dialog_service.get_conversations_by_agent(agent_id)
    else:
        # Get all conversations (would need a method for this)
        from app.models.agent_conversation import AgentConversation
        query = db.query(AgentConversation)
        if status:
            query = query.filter(AgentConversation.status == status)
        conversations = query.order_by(AgentConversation.created_at.desc()).all()
    
    return [conv.to_dict() for conv in conversations]


@router.post("/{conversation_id}/message", response_model=MessageResponse)
async def add_message(
    conversation_id: UUID,
    message_data: MessageAdd,
    db: Session = Depends(get_db)
):
    """
    Add a message to a conversation
    
    The agent must be a participant in the conversation.
    """
    try:
        dialog_service = AgentDialogService(db)
        
        # Validate role
        role = MessageRole.AGENT
        if message_data.role:
            try:
                role = MessageRole(message_data.role)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid role: {message_data.role}")
        
        message = dialog_service.add_message(
            conversation_id=conversation_id,
            agent_id=message_data.agent_id,
            content=message_data.content,
            role=role,
            metadata=message_data.metadata
        )
        
        return MessageResponse(
            id=message.get("id", ""),
            agent_id=message.get("agent_id", str(message_data.agent_id)),
            role=message.get("role", role.value),
            content=message.get("content", message_data.content),
            timestamp=message.get("timestamp", datetime.utcnow().isoformat()),
            metadata=message.get("metadata")
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{conversation_id}/send-message", response_model=MessageResponse)
async def send_message_to_participants(
    conversation_id: UUID,
    message_data: MessageSend,
    db: Session = Depends(get_db)
):
    """
    Send a message in conversation and notify other participants via A2A protocol
    
    This will:
    1. Add the message to the conversation
    2. Send A2A notifications to other participants
    """
    try:
        dialog_service = AgentDialogService(db)
        
        message = await dialog_service.send_message_to_participants(
            conversation_id=conversation_id,
            sender_agent_id=message_data.sender_agent_id,
            content=message_data.content,
            recipient_agent_ids=message_data.recipient_agent_ids,
            metadata=message_data.metadata
        )
        
        return MessageResponse(
            id=message.get("id", ""),
            agent_id=message.get("agent_id", str(message_data.sender_agent_id)),
            role=message.get("role", MessageRole.AGENT.value),
            content=message.get("content", message_data.content),
            timestamp=message.get("timestamp", datetime.utcnow().isoformat()),
            metadata=message.get("metadata")
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error sending message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.put("/{conversation_id}/context", response_model=Dict[str, Any])
async def update_context(
    conversation_id: UUID,
    context_update: ContextUpdate,
    db: Session = Depends(get_db)
):
    """Update conversation context"""
    try:
        dialog_service = AgentDialogService(db)
        
        context = dialog_service.update_context(
            conversation_id=conversation_id,
            updates=context_update.updates
        )
        
        return context
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{conversation_id}/complete", response_model=ConversationResponse)
async def complete_conversation(
    conversation_id: UUID,
    success: bool = Query(True, description="Whether conversation completed successfully"),
    result: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_db)
):
    """Mark conversation as completed"""
    try:
        dialog_service = AgentDialogService(db)
        
        completed = dialog_service.complete_conversation(
            conversation_id=conversation_id,
            success=success,
            result=result
        )
        
        return completed.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error completing conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{conversation_id}/pause", response_model=ConversationResponse)
async def pause_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db)
):
    """Pause a conversation"""
    try:
        dialog_service = AgentDialogService(db)
        paused = dialog_service.pause_conversation(conversation_id)
        return paused.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error pausing conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/{conversation_id}/resume", response_model=ConversationResponse)
async def resume_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db)
):
    """Resume a paused conversation"""
    try:
        dialog_service = AgentDialogService(db)
        resumed = dialog_service.resume_conversation(conversation_id)
        return resumed.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error resuming conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all messages in a conversation"""
    dialog_service = AgentDialogService(db)
    conversation = dialog_service.get_conversation(conversation_id)
    
    if not conversation:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
    
    messages = conversation.get_messages()
    return [
        MessageResponse(
            id=msg.get("id", ""),
            agent_id=msg.get("agent_id", ""),
            role=msg.get("role", MessageRole.AGENT.value),
            content=msg.get("content", ""),
            timestamp=msg.get("timestamp", ""),
            metadata=msg.get("metadata")
        )
        for msg in messages
    ]

