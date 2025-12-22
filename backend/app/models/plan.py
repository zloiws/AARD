"""
Plan model for task planning
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class PlanStatus(str, Enum):
    """Plan status enumeration"""
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Plan(Base):
    """Plan model for task planning"""
    __tablename__ = "plans"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    
    # Plan structure
    goal = Column(Text, nullable=False)
    strategy = Column(JSON, nullable=True)  # approach, assumptions, constraints, success_criteria
    steps = Column(JSON, nullable=False)  # array of steps
    alternatives = Column(JSON, nullable=True)  # alternative approaches
    
    # Status - use String instead of SQLEnum to match DB constraint (lowercase)
    status = Column(String, nullable=False, default="draft")
    current_step = Column(Integer, nullable=False, default=0)
    
    # Metrics
    estimated_duration = Column(Integer, nullable=True)  # seconds
    actual_duration = Column(Integer, nullable=True)  # seconds
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    approved_at = Column(DateTime, nullable=True)
    
    # Relationships
    task = relationship("Task", backref="plans")
    approval_request = relationship("ApprovalRequest", back_populates="plan", uselist=False, overlaps="approval_requests")
    traces = relationship("ExecutionTrace", back_populates="plan", foreign_keys="ExecutionTrace.plan_id")
    # Optional agent metadata (agent id, preferences) stored as JSON
    agent_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<Plan(id={self.id}, task_id={self.task_id}, version={self.version}, status={self.status})>"

