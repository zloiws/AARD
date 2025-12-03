"""
Learning Pattern model for meta-learning system
Stores patterns learned from execution history for self-improvement
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class PatternType(str, Enum):
    """Type of learning pattern"""
    STRATEGY = "strategy"  # Planning strategy patterns
    PROMPT = "prompt"  # Prompt improvement patterns
    TOOL_SELECTION = "tool_selection"  # Tool selection patterns
    CODE_PATTERN = "code_pattern"  # Code generation patterns
    ERROR_RECOVERY = "error_recovery"  # Error recovery patterns


class LearningPattern(Base):
    """Learning pattern extracted from execution history"""
    __tablename__ = "learning_patterns"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Pattern identification
    pattern_type = Column(String(50), nullable=False)  # strategy, prompt, tool_selection, etc.
    name = Column(String(255), nullable=False)  # Human-readable pattern name
    description = Column(Text, nullable=True)  # Pattern description
    
    # Pattern data (JSON)
    pattern_data = Column(JSONB, nullable=False)  # Actual pattern data (varies by type)
    
    # Performance metrics
    success_rate = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    usage_count = Column(Integer, nullable=False, default=0)  # How many times pattern was used
    total_executions = Column(Integer, nullable=False, default=0)  # Total executions using this pattern
    successful_executions = Column(Integer, nullable=False, default=0)  # Successful executions
    
    # Context
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    task_category = Column(String(100), nullable=True)  # Category of tasks this pattern applies to
    tags = Column(JSONB, nullable=True)  # Tags for categorization
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)  # Last time pattern was used
    
    # Relationships
    agent = relationship("Agent", backref="learning_patterns")
    
    def __repr__(self):
        return f"<LearningPattern(id={self.id}, type={self.pattern_type}, name={self.name}, success_rate={self.success_rate:.2f})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary"""
        return {
            "id": str(self.id),
            "pattern_type": self.pattern_type,
            "name": self.name,
            "description": self.description,
            "pattern_data": self.pattern_data,
            "success_rate": self.success_rate,
            "usage_count": self.usage_count,
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "agent_id": str(self.agent_id) if self.agent_id else None,
            "task_category": self.task_category,
            "tags": self.tags,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

