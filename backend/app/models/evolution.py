"""
Evolution history and feedback models
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class EntityType(str, Enum):
    """Entity type enumeration"""
    ARTIFACT = "artifact"
    PROMPT = "prompt"
    AGENT_BEHAVIOR = "agent_behavior"
    TOOL_BEHAVIOR = "tool_behavior"
    TASK = "task"
    PLAN = "plan"
    AGENT = "agent"
    TOOL = "tool"


class ChangeType(str, Enum):
    """Change type enumeration"""
    CREATED = "created"
    UPDATED = "updated"
    IMPROVED = "improved"
    DEPRECATED = "deprecated"
    OPTIMIZED = "optimized"


class TriggerType(str, Enum):
    """Trigger type enumeration"""
    USER_FEEDBACK = "user_feedback"
    ERROR_ANALYSIS = "error_analysis"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    AUTO_OPTIMIZATION = "auto_optimization"
    MANUAL_REQUEST = "manual_request"


class EvolutionHistory(Base):
    """Evolution history model"""
    __tablename__ = "evolution_history"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    entity_id = Column(PGUUID(as_uuid=True), nullable=False)
    
    # Change information
    change_type = Column(SQLEnum(ChangeType), nullable=True)
    change_description = Column(Text, nullable=True)
    before_state = Column(JSON, nullable=True)
    after_state = Column(JSON, nullable=True)
    
    # Trigger information
    trigger_type = Column(SQLEnum(TriggerType), nullable=True)
    trigger_data = Column(JSON, nullable=True)
    
    # Results
    improvement_metrics = Column(JSON, nullable=True)
    success = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def __repr__(self):
        return f"<EvolutionHistory(id={self.id}, entity={self.entity_type}:{self.entity_id}, change={self.change_type})>"


class FeedbackType(str, Enum):
    """Feedback type enumeration"""
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    CONTEXTUAL = "contextual"


class Feedback(Base):
    """Feedback model"""
    __tablename__ = "feedback"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type = Column(SQLEnum(EntityType), nullable=False)
    entity_id = Column(PGUUID(as_uuid=True), nullable=False)
    
    feedback_type = Column(SQLEnum(FeedbackType), nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5
    comment = Column(Text, nullable=True)
    
    # Context
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    session_id = Column(String(255), nullable=True)
    
    # Processing
    processed = Column(Boolean, nullable=False, default=False)
    insights_extracted = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    task = relationship("Task", backref="feedback")
    
    def __repr__(self):
        return f"<Feedback(id={self.id}, entity={self.entity_type}:{self.entity_id}, rating={self.rating})>"

