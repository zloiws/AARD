"""
Prompt model for evolution system
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class PromptType(str, Enum):
    """Prompt type enumeration"""
    SYSTEM = "system"
    AGENT = "agent"
    TOOL = "tool"
    META = "meta"
    CONTEXT = "context"


class PromptStatus(str, Enum):
    """Prompt status enumeration"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    TESTING = "testing"


class Prompt(Base):
    """Prompt model for storing and evolving prompts"""
    __tablename__ = "prompts"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    prompt_text = Column(Text, nullable=False)
    prompt_type = Column(String(50), nullable=False)  # Use String instead of Enum to match DB
    level = Column(Integer, nullable=False, default=0)  # 0-4
    version = Column(Integer, nullable=False, default=1)
    parent_prompt_id = Column(PGUUID(as_uuid=True), ForeignKey("prompts.id"), nullable=True)
    status = Column(String(20), nullable=False, default="active")  # Use string to match DB constraint
    
    # Metrics
    success_rate = Column(Float, nullable=True)
    avg_execution_time = Column(Float, nullable=True)
    user_rating = Column(Float, nullable=True)
    usage_count = Column(Integer, nullable=False, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(255), nullable=True)
    last_improved_at = Column(DateTime, nullable=True)
    improvement_history = Column(JSON, nullable=True)
    
    # Relationships
    parent_prompt = relationship("Prompt", remote_side=[id], backref="versions")
    
    def __repr__(self):
        return f"<Prompt(id={self.id}, name={self.name}, type={self.prompt_type}, version={self.version})>"

