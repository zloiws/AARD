"""
Task model
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from typing import Dict, Any, Optional

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
    
    # Digital Twin: Central context storage for all task-related data
    # Stores:
    # - original_user_request: Original user request/query
    # - active_todos: Current ToDo list (from plan steps)
    # - historical_todos: Historical ToDo lists (plan versions)
    # - artifacts: Generated artifacts (prompts, code, tables, etc.)
    # - execution_logs: Execution logs, errors, validation results
    # - interaction_history: History of human interactions (approvals, corrections, feedback)
    # - metadata: Additional metadata (model used, timestamps, etc.)
    context = Column(JSONB, nullable=True, comment="Digital Twin context: stores all task-related data")
    
    # Relationships
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    traces = relationship("ExecutionTrace", foreign_keys="ExecutionTrace.task_id", overlaps="task")
    
    def get_context(self) -> Dict[str, Any]:
        """Get task context, initializing if empty"""
        if self.context is None:
            return {}
        return self.context if isinstance(self.context, dict) else {}
    
    def update_context(self, updates: Dict[str, Any], merge: bool = True) -> None:
        """Update task context with new data"""
        current = self.get_context()
        if merge:
            current.update(updates)
            self.context = current
        else:
            self.context = updates
    
    def add_to_history(self, history_type: str, data: Dict[str, Any]) -> None:
        """Add entry to interaction history in context"""
        context = self.get_context()
        if "interaction_history" not in context:
            context["interaction_history"] = []
        
        history_entry = {
            "type": history_type,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }
        context["interaction_history"].append(history_entry)
        self.context = context
    
    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, description={self.description[:50]}...)>"

