"""
Agent Conversation model for AARD platform
Represents dialogs between agents for collaborative task solving
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from app.core.database import Base
from sqlalchemy import (JSON, Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class ConversationStatus(str, Enum):
    """Conversation status enumeration"""
    INITIATED = "initiated"  # Conversation started, waiting for first message
    ACTIVE = "active"  # Conversation is ongoing
    PAUSED = "paused"  # Conversation temporarily paused
    COMPLETED = "completed"  # Conversation completed successfully
    FAILED = "failed"  # Conversation failed
    CANCELLED = "cancelled"  # Conversation cancelled


class MessageRole(str, Enum):
    """Message role in conversation"""
    AGENT = "agent"  # Message from an agent
    SYSTEM = "system"  # System message
    USER = "user"  # User message (if user participates)


class AgentConversation(Base):
    """
    Agent Conversation model - represents a dialog between agents
    
    Stores:
    - participants: List of agent IDs participating in the conversation
    - messages: List of messages in the conversation
    - context: Conversation context (shared knowledge, state, etc.)
    - goal: Goal of the conversation (what agents are trying to achieve)
    - task_id: Optional link to a task this conversation is related to
    """
    __tablename__ = "agent_conversations"
    
    # Primary identification
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Conversation metadata
    title = Column(String(255), nullable=True)  # Optional title for the conversation
    description = Column(Text, nullable=True)  # Optional description
    
    # Participants - list of agent IDs participating in the conversation
    participants = Column(JSONB, nullable=False)  # List of UUIDs: [agent_id1, agent_id2, ...]
    
    # Messages - list of conversation messages
    # Format: [
    #   {
    #     "id": "message_id",
    #     "agent_id": "agent_uuid",
    #     "role": "agent|system|user",
    #     "content": "message text",
    #     "timestamp": "2024-01-01T00:00:00",
    #     "metadata": {...}
    #   },
    #   ...
    # ]
    messages = Column(JSONB, nullable=False, default=list)  # List of message objects
    
    # Context - shared context for the conversation
    # Stores: shared knowledge, state, intermediate results, etc.
    context = Column(JSONB, nullable=True)  # Dict with conversation context
    
    # Goal - what agents are trying to achieve in this conversation
    goal = Column(Text, nullable=True)  # Goal description
    
    # Status and lifecycle
    status = Column(String(50), nullable=False, default=ConversationStatus.INITIATED.value)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)  # When conversation was completed
    
    # Relationships
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)  # Optional link to task
    task = relationship("Task", backref="conversations")
    
    # Additional metadata
    conversation_metadata = Column(JSONB, nullable=True)  # Additional metadata
    
    def __repr__(self):
        return f"<AgentConversation(id={self.id}, status={self.status}, participants={len(self.participants) if self.participants else 0})>"
    
    def add_message(
        self,
        agent_id: UUID,
        content: str,
        role: MessageRole = MessageRole.AGENT,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to the conversation
        
        Args:
            agent_id: ID of the agent sending the message
            content: Message content
            role: Message role (agent, system, user)
            metadata: Optional message metadata
            
        Returns:
            Created message object
        """
        if not self.messages:
            self.messages = []
        
        message = {
            "id": str(uuid4()),
            "agent_id": str(agent_id),
            "role": role.value if isinstance(role, MessageRole) else role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)
        
        # Update status to active if it was initiated
        if self.status == ConversationStatus.INITIATED.value:
            self.status = ConversationStatus.ACTIVE.value
        
        return message
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get all messages in the conversation"""
        return self.messages if self.messages else []
    
    def get_participants(self) -> List[UUID]:
        """Get list of participant agent IDs"""
        if not self.participants:
            return []
        return [UUID(pid) if isinstance(pid, str) else pid for pid in self.participants]
    
    def is_participant(self, agent_id: UUID) -> bool:
        """Check if an agent is a participant in this conversation"""
        participants = self.get_participants()
        return agent_id in participants
    
    def get_context(self) -> Dict[str, Any]:
        """Get conversation context"""
        return self.context if self.context else {}
    
    def update_context(self, updates: Dict[str, Any]):
        """Update conversation context with new data"""
        if not self.context:
            self.context = {}
        # Create a new dict to ensure JSONB mutability
        current_context = dict(self.context) if self.context else {}
        current_context.update(updates)
        self.context = current_context
        self.updated_at = datetime.now(timezone.utc)
    
    def complete(self, success: bool = True):
        """Mark conversation as completed"""
        self.status = ConversationStatus.COMPLETED.value if success else ConversationStatus.FAILED.value
        self.completed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary"""
        return {
            "id": str(self.id),
            "title": self.title,
            "description": self.description,
            "participants": [str(pid) for pid in self.get_participants()],
            "messages": self.get_messages(),
            "context": self.get_context(),
            "goal": self.goal,
            "status": self.status,
            "task_id": str(self.task_id) if self.task_id else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.conversation_metadata or {}
        }

