"""
Workflow Event model for persistent storage of workflow execution events
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class EventSource(str, Enum):
    """Source of the event"""
    USER = "user"
    PLANNER_AGENT = "planner_agent"
    CODER_AGENT = "coder_agent"
    VALIDATOR = "validator"
    TOOL = "tool"
    SYSTEM = "system"
    MODEL = "model"


class EventType(str, Enum):
    """Type of workflow event"""
    USER_INPUT = "user_input"
    MODEL_REQUEST = "model_request"
    MODEL_RESPONSE = "model_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    PLAN_UPDATE = "plan_update"
    APPROVAL_REQUEST = "approval_request"
    APPROVAL_RESPONSE = "approval_response"
    EXECUTION_STEP = "execution_step"
    ERROR = "error"
    COMPLETION = "completion"
    STATUS_CHANGE = "status_change"


class EventStatus(str, Enum):
    """Event execution status"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PENDING = "pending"


class WorkflowStage(str, Enum):
    """Workflow execution stage"""
    USER_REQUEST = "user_request"
    REQUEST_PARSING = "request_parsing"
    ACTION_DETERMINATION = "action_determination"
    EXECUTION = "execution"
    RESULT = "result"
    ERROR = "error"


class WorkflowEvent(Base):
    """
    Persistent model for workflow execution events
    Stores all events with full detail for observability and audit
    """
    __tablename__ = "workflow_events"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Workflow identification
    workflow_id = Column(String(255), nullable=False, index=True)  # Can be task_id, chat_session_id, etc.
    
    # Event classification
    event_type = Column(String(50), nullable=False, index=True)
    event_source = Column(String(50), nullable=False, index=True)
    stage = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default=EventStatus.IN_PROGRESS.value)
    
    # Human-readable message
    message = Column(Text, nullable=False)
    
    # Detailed event data (JSONB for flexibility)
    event_data = Column(JSONB, nullable=True)  # Full prompt, response, tool call details, etc.
    event_metadata = Column("metadata", JSONB, nullable=True)  # Additional metadata (model, server, duration, etc.) - using Column name to avoid SQLAlchemy reserved word
    
    # Relationships to other entities
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    plan_id = Column(PGUUID(as_uuid=True), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True, index=True)
    tool_id = Column(PGUUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="SET NULL"), nullable=True, index=True)
    approval_request_id = Column(PGUUID(as_uuid=True), ForeignKey("approval_requests.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)  # Chat session ID
    
    # Tracing
    trace_id = Column(String(255), nullable=True, index=True)  # OpenTelemetry trace ID
    parent_event_id = Column(PGUUID(as_uuid=True), ForeignKey("workflow_events.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Timing (millisecond precision)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)
    duration_ms = Column(Integer, nullable=True)  # Duration of the event if applicable
    
    # Relationships
    task = relationship("Task", backref="workflow_events")
    plan = relationship("Plan", backref="workflow_events")
    tool = relationship("Artifact", backref="workflow_events")
    approval_request = relationship("ApprovalRequest", backref="workflow_events")
    parent_event = relationship("WorkflowEvent", remote_side=[id], backref="child_events")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_workflow_events_workflow_id", "workflow_id"),
        Index("idx_workflow_events_timestamp", "timestamp"),
        Index("idx_workflow_events_type_source", "event_type", "event_source"),
        Index("idx_workflow_events_stage_status", "stage", "status"),
        Index("idx_workflow_events_task_id", "task_id"),
        Index("idx_workflow_events_trace_id", "trace_id"),
        Index("idx_workflow_events_session_id", "session_id"),
        CheckConstraint("status IN ('in_progress', 'completed', 'failed', 'cancelled', 'pending')", name="workflow_events_status_check"),
    )
    
    def __repr__(self):
        return f"<WorkflowEvent(id={self.id}, workflow_id={self.workflow_id}, type={self.event_type}, stage={self.stage})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": str(self.id),
            "workflow_id": self.workflow_id,
            "event_type": self.event_type,
            "event_source": self.event_source,
            "stage": self.stage,
            "status": self.status,
            "message": self.message,
            "event_data": self.event_data or {},
            "metadata": self.event_metadata or {},
            "task_id": str(self.task_id) if self.task_id else None,
            "plan_id": str(self.plan_id) if self.plan_id else None,
            "tool_id": str(self.tool_id) if self.tool_id else None,
            "approval_request_id": str(self.approval_request_id) if self.approval_request_id else None,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "parent_event_id": str(self.parent_event_id) if self.parent_event_id else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "duration_ms": self.duration_ms
        }

