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
    """Task status enumeration"""
    PENDING = "pending"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(Base):
    """Task model"""
    __tablename__ = "tasks"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    description = Column(Text, nullable=False)
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(Integer, default=5, nullable=False)  # 0-9, where 9 is highest
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    parent_task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id"), nullable=True)
    plan_id = Column(PGUUID(as_uuid=True), nullable=True)  # Will reference plans table when created
    current_checkpoint_id = Column(PGUUID(as_uuid=True), nullable=True)
    
    # Relationships
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    traces = relationship("ExecutionTrace", foreign_keys="ExecutionTrace.task_id")
    
    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, description={self.description[:50]}...)>"

