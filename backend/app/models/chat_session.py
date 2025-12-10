"""
Chat session and message models for persistent storage
"""
from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class ChatSession(Base):
    """Chat session stored in database"""
    __tablename__ = "chat_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    system_prompt = Column(Text, nullable=True)
    title = Column(String(255), nullable=True)
    
    # User identifier (for future multi-user support)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Metadata stored as JSONB (using different name to avoid SQLAlchemy reserved word)
    session_metadata = Column("metadata", JSON, default={}, nullable=True)
    
    # Relationship to messages
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, title={self.title}, messages_count={len(self.messages)})>"


class ChatMessage(Base):
    """Chat message stored in database"""
    __tablename__ = "chat_messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String(50), nullable=False)  # "user", "assistant", "system"
    content = Column(Text, nullable=False)
    
    model = Column(String(255), nullable=True)  # Model used for assistant messages
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Metadata stored as JSONB (duration, tokens, etc.) (using different name to avoid SQLAlchemy reserved word)
    message_metadata = Column("metadata", JSON, default={}, nullable=True)
    
    # Sequence number for ordering messages within session
    sequence = Column(Integer, nullable=False, default=0)
    
    # Relationship to session
    session = relationship("ChatSession", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role={self.role}, content_length={len(self.content) if self.content else 0})>"

