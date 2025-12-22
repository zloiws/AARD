"""
SQLAlchemy model for execution traces
"""
import uuid
from datetime import datetime, timezone

from app.core.database import Base
from sqlalchemy import (CheckConstraint, Column, DateTime, ForeignKey, Index,
                        Integer, String)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class ExecutionTrace(Base):
    """
    Execution trace model for storing OpenTelemetry traces
    """
    __tablename__ = "execution_traces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trace_id = Column(String(255), nullable=False, index=True)  # OpenTelemetry trace ID
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)
    span_id = Column(String(255), nullable=True, index=True)
    parent_span_id = Column(String(255), nullable=True, index=True)
    operation_name = Column(String(255), nullable=False)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    status = Column(
        String(20),
        CheckConstraint("status IN ('success', 'error', 'timeout')"),
        nullable=True,
        index=True
    )
    attributes = Column(JSONB, nullable=True)
    agent_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    tool_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    error_message = Column(String(1000), nullable=True)
    error_type = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships (using strings to avoid circular imports)
    task = relationship("Task", foreign_keys=[task_id], overlaps="traces")
    plan = relationship("Plan", foreign_keys=[plan_id])
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_traces_trace_id", "trace_id"),
        Index("idx_traces_task_id", "task_id"),
        Index("idx_traces_plan_id", "plan_id"),
        Index("idx_traces_agent_id", "agent_id"),
        Index("idx_traces_start_time", "start_time"),
        Index("idx_traces_status", "status"),
        Index("idx_traces_operation", "operation_name"),
    )
    
    def __repr__(self):
        return f"<ExecutionTrace(id={self.id}, trace_id={self.trace_id}, operation={self.operation_name}, status={self.status})>"

