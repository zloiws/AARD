"""
Task model
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TaskStatus(str, Enum):
    """Task status enumeration with full workflow lifecycle"""
    # Initial states
    DRAFT = "draft"  # Created by planner, not yet approved
    PENDING = "pending"  # Waiting to start
    PLANNING = "planning"  # Plan is being generated
    
    # Approval states
    PENDING_APPROVAL = "pending_approval"  # Sent for approval
    WAITING_APPROVAL = "waiting_approval"  # Waiting for approval (legacy, use PENDING_APPROVAL)
    APPROVED = "approved"  # Approved by human/validator
    
    # Execution states
    IN_PROGRESS = "in_progress"  # Task is executing
    EXECUTING = "executing"  # Plan is executing (legacy, use IN_PROGRESS)
    PAUSED = "paused"  # Temporarily paused
    ON_HOLD = "on_hold"  # On hold (waiting for data, human, external event)
    
    # Final states
    COMPLETED = "completed"  # Successfully completed
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # Cancelled by human or system


class Task(Base):
    """Task model"""
    __tablename__ = "tasks"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(Integer, default=5, nullable=False)  # 0-9, where 9 is highest
    
    # Role tracking for workflow
    created_by = Column(String(255))  # User who created the task
    created_by_role = Column(String(50), nullable=True)  # Role: planner, human, system
    approved_by = Column(String(255), nullable=True)  # User who approved
    approved_by_role = Column(String(50), nullable=True)  # Role: human, validator
    
    # Graduated autonomy level (0-4)
    autonomy_level = Column(Integer, default=2, nullable=False)  # 0=read-only, 1=step-by-step, 2=plan approval, 3=autonomous with notification, 4=full autonomous
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    parent_task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    plan_id = Column(PGUUID(as_uuid=True), nullable=True)  # Will reference plans table when created
    current_checkpoint_id = Column(PGUUID(as_uuid=True), nullable=True)
    
    # Relationships
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    traces = relationship("ExecutionTrace", foreign_keys="ExecutionTrace.task_id", overlaps="task")
    
    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, description={self.description[:50]}...)>"

