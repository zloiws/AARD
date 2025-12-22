"""
SQLAlchemy models for task queues
"""
import uuid
from datetime import datetime, timezone

from app.core.database import Base
from sqlalchemy import (Boolean, CheckConstraint, Column, DateTime, ForeignKey,
                        Index, Integer, String, Text)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class TaskQueue(Base):
    """
    Task queue model for managing queues
    """
    __tablename__ = "task_queues"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    max_concurrent = Column(Integer, default=1, nullable=False)
    priority = Column(Integer, default=5, nullable=False)  # 0-9, where 9 is highest
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    tasks = relationship("QueueTask", back_populates="queue", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_task_queues_name", "name"),
        Index("idx_task_queues_active", "is_active"),
        Index("idx_task_queues_priority", "priority"),
    )
    
    def __repr__(self):
        return f"<TaskQueue(id={self.id}, name={self.name}, max_concurrent={self.max_concurrent})>"


class QueueTask(Base):
    """
    Queue task model for tasks in queues
    """
    __tablename__ = "queue_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    queue_id = Column(UUID(as_uuid=True), ForeignKey("task_queues.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Task information
    task_type = Column(String(50), nullable=False, index=True)  # plan_execution, artifact_generation, etc.
    task_data = Column(JSONB, nullable=False)
    priority = Column(Integer, default=5, nullable=False, index=True)  # 0-9
    
    # Status
    status = Column(
        String(20),
        CheckConstraint("status IN ('pending', 'queued', 'processing', 'completed', 'failed', 'cancelled')"),
        nullable=False,
        default="pending",
        index=True
    )
    
    # Retry
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    
    # Result
    result_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    assigned_worker = Column(String(255), nullable=True, index=True)  # Worker ID
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    queue = relationship("TaskQueue", back_populates="tasks")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_queue_tasks_status", "status"),
        Index("idx_queue_tasks_priority", "priority"),
        Index("idx_queue_tasks_next_retry", "next_retry_at"),
        Index("idx_queue_tasks_queue", "queue_id"),
        Index("idx_queue_tasks_type", "task_type"),
        Index("idx_queue_tasks_worker", "assigned_worker"),
        Index("idx_queue_tasks_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<QueueTask(id={self.id}, type={self.task_type}, status={self.status}, priority={self.priority})>"

