"""
Agent memory models for short-term and long-term memory
"""
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class MemoryType(str, Enum):
    """Memory type enumeration"""
    FACT = "fact"  # Factual information
    EXPERIENCE = "experience"  # Experience from task execution
    WORKING = "working"  # Active ToDo / working memory
    PATTERN = "pattern"  # Recognized patterns
    PROCEDURAL = "procedural"  # Procedural patterns / strategies
    RULE = "rule"  # Rules and guidelines
    CONTEXT = "context"  # Contextual information


class AssociationType(str, Enum):
    """Memory association type enumeration"""
    RELATED = "related"  # Related memories
    CAUSAL = "causal"  # Causal relationship
    SIMILAR = "similar"  # Similar situations
    OPPOSITE = "opposite"  # Opposite situations
    PREREQUISITE = "prerequisite"  # Prerequisite knowledge


class AgentMemory(Base):
    """Long-term memory for agents"""
    __tablename__ = "agent_memories"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    # Memory content
    memory_type = Column(String(50), nullable=False)  # MemoryType enum
    content = Column(JSONB, nullable=False)  # Memory content (flexible structure)
    summary = Column(Text, nullable=True)  # Human-readable summary
    
    # Vector embedding for semantic search
    # Note: embedding is stored as vector type in DB, but SQLAlchemy can't read it directly
    # Use raw SQL to read/write embeddings (see MemoryService)
    embedding = Column(ARRAY(Float), nullable=True)  # Embedding column (array of floats) - use raw SQL for vector ops if available
    
    # Importance and access tracking
    importance = Column(Float, default=0.5, nullable=False)  # 0.0 to 1.0
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)
    
    # Metadata
    tags = Column(JSONB, nullable=True)  # Tags for categorization
    source = Column(String(255), nullable=True)  # Source of memory (task_id, user, etc.)
    
    # Lifecycle
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    
    # Relationships
    agent = relationship("Agent", backref="memories")
    associations = relationship(
        "MemoryAssociation",
        foreign_keys="MemoryAssociation.memory_id",
        back_populates="memory",
        cascade="all, delete-orphan"
    )
    related_associations = relationship(
        "MemoryAssociation",
        foreign_keys="MemoryAssociation.related_memory_id",
        back_populates="related_memory"
    )
    
    def __repr__(self):
        return f"<AgentMemory(id={self.id}, agent_id={self.agent_id}, type={self.memory_type}, importance={self.importance})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert memory to dictionary"""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "memory_type": self.memory_type,
            "content": self.content,
            "summary": self.summary,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at.isoformat() if self.last_accessed_at else None,
            "tags": self.tags,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            # Note: embedding is not accessible via SQLAlchemy - use raw SQL to check
        }


class MemoryEntry(Base):
    """Short-term memory for agents (session context)"""
    __tablename__ = "memory_entries"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    
    # Context identification
    session_id = Column(String(255), nullable=True)  # Session or task ID
    context_key = Column(String(255), nullable=False)  # Key for context lookup
    
    # Content
    content = Column(JSONB, nullable=False)  # Context data
    
    # TTL
    ttl_seconds = Column(Integer, nullable=True)  # Time to live in seconds
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime, nullable=True)  # Calculated from ttl_seconds
    
    # Relationships
    agent = relationship("Agent", backref="memory_entries")
    
    def __repr__(self):
        return f"<MemoryEntry(id={self.id}, agent_id={self.agent_id}, context_key={self.context_key})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entry to dictionary"""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "session_id": self.session_id,
            "context_key": self.context_key,
            "content": self.content,
            "ttl_seconds": self.ttl_seconds,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    def is_expired(self) -> bool:
        """Check if entry is expired"""
        if not self.expires_at:
            return False
        expires_at = self.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > expires_at


class MemoryAssociation(Base):
    """Associations between memories"""
    __tablename__ = "memory_associations"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    memory_id = Column(PGUUID(as_uuid=True), ForeignKey("agent_memories.id", ondelete="CASCADE"), nullable=False)
    related_memory_id = Column(PGUUID(as_uuid=True), ForeignKey("agent_memories.id", ondelete="CASCADE"), nullable=False)
    
    # Association properties
    association_type = Column(String(50), nullable=False)  # AssociationType enum
    strength = Column(Float, default=0.5, nullable=False)  # 0.0 to 1.0
    
    # Metadata
    description = Column(Text, nullable=True)  # Description of association
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    memory = relationship("AgentMemory", foreign_keys=[memory_id], back_populates="associations")
    related_memory = relationship("AgentMemory", foreign_keys=[related_memory_id], back_populates="related_associations")
    
    def __repr__(self):
        return f"<MemoryAssociation(id={self.id}, memory_id={self.memory_id}, related_id={self.related_memory_id}, type={self.association_type})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert association to dictionary"""
        return {
            "id": str(self.id),
            "memory_id": str(self.memory_id),
            "related_memory_id": str(self.related_memory_id),
            "association_type": self.association_type,
            "strength": self.strength,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }

