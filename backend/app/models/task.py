"""
Task model
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from typing import Dict, Any, Optional
from sqlalchemy.ext.mutable import MutableDict

from app.core.database import Base
import logging
import traceback


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
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
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
    # Use MutableDict to ensure in-place modifications to the JSONB are tracked by SQLAlchemy
    context = Column(MutableDict.as_mutable(JSONB), nullable=True, comment="Digital Twin context: stores all task-related data")
    
    # Relationships
    parent_task = relationship("Task", remote_side=[id], backref="subtasks")
    traces = relationship("ExecutionTrace", foreign_keys="ExecutionTrace.task_id", overlaps="task")
    
    def get_context(self) -> Dict[str, Any]:
        """Get task context, initializing if empty"""
        if self.context is None:
            current = {}
        else:
            current = self.context if isinstance(self.context, dict) else {}

        # Backwards-compatibility: ensure original_user_request is always available
        try:
            if "original_user_request" not in current and self.description:
                current["original_user_request"] = self.description
        except Exception:
            pass
        # Ensure active_todos present if possible by inspecting related plans
        try:
            if "active_todos" not in current:
                # Try to use related plans (if loaded) to build todos
                plans = getattr(self, "plans", None)
                if plans:
                    last_plan = plans[-1] if len(plans) > 0 else None
                    if last_plan and getattr(last_plan, "steps", None):
                        steps = last_plan.steps if isinstance(last_plan.steps, list) else []
                        current["active_todos"] = [
                            {
                                "step_id": step.get("step_id", f"step_{i}"),
                                "description": step.get("description", ""),
                                "status": "pending",
                                "completed": False
                            }
                            for i, step in enumerate(steps)
                        ]
                    else:
                        current.setdefault("active_todos", [])
                else:
                    current.setdefault("active_todos", [])
        except Exception:
            # best-effort; don't fail if relationship not available
            current.setdefault("active_todos", [])

        # If active_todos exists but is empty, add a fallback todo based on task description
        try:
            if isinstance(current.get("active_todos", None), list) and len(current.get("active_todos", [])) == 0:
                if self.description:
                    current["active_todos"] = [{
                        "step_id": "step_1",
                        "description": self.description,
                        "status": "pending",
                        "completed": False
                    }]
        except Exception:
            pass

        # Ensure 'plan' exists in context as a minimal fallback
        try:
            if "plan" not in current:
                current["plan"] = {
                    "plan_id": None,
                    "version": 1,
                    "goal": self.description or "",
                    "strategy": {},
                    "steps_count": 0,
                    "status": "draft",
                    "created_at": None
                }
        except Exception:
            pass

        # Try to populate plan_id/version from DB if possible (best-effort)
        try:
            if current.get("plan", {}).get("plan_id") is None:
                from app.core.database import SessionLocal
                from app.models.plan import Plan
                s = SessionLocal()
                try:
                    p = s.query(Plan).filter(Plan.task_id == self.id).order_by(Plan.created_at.desc()).first()
                    if p:
                        current["plan"]["plan_id"] = str(p.id)
                        current["plan"]["version"] = p.version
                        current["plan"]["goal"] = p.goal
                        current["plan"]["strategy"] = p.strategy if isinstance(p.strategy, dict) else {}
                        current["plan"]["steps_count"] = len(p.steps) if p.steps else 0
                        current["plan"]["status"] = p.status
                        current["plan"]["created_at"] = p.created_at.isoformat() if p.created_at else None
                finally:
                    s.close()
        except Exception:
            pass

        return current
    
    def update_context(self, updates: Dict[str, Any], merge: bool = True) -> None:
        """Update task context with new data"""
        logger = logging.getLogger("app.models.task")
        try:
            current = self.get_context()
            if merge:
                # Debug logging to trace context mutations (only log keys to avoid big payloads)
                try:
                    logger.debug(f"update_context merge called for task {self.id}; keys={list(updates.keys())}")
                    if "artifacts" in updates:
                        # Surface artifact updates at INFO so they appear in test logs
                        logger.info(f"update_context: artifacts updated for task {self.id}; count={len(updates.get('artifacts') or [])}")
                        try:
                            # Also print to stdout for immediate test-run visibility
                            print(f"[TRACE] update_context ARTIFACTS for task {self.id}; count={len(updates.get('artifacts') or [])}")
                            try:
                                import inspect
                                caller = inspect.stack()[1]
                                print(f"[TRACE] update_context called from {caller.filename}:{caller.lineno} in {caller.function}")
                            except Exception:
                                pass
                        except Exception:
                            pass
                except Exception:
                    pass
                # Defensive: avoid overwriting existing non-empty artifacts with empty lists
                try:
                    current_artifacts = current.get("artifacts")
                    incoming_artifacts = updates.get("artifacts") if isinstance(updates.get("artifacts"), list) else None
                    if isinstance(incoming_artifacts, list) and len(incoming_artifacts) == 0 and isinstance(current_artifacts, list) and len(current_artifacts) > 0:
                        updates = {k: v for k, v in updates.items() if k != "artifacts"}
                except Exception:
                    pass
                current.update(updates)
                self.context = current
            else:
                try:
                    logger.debug(f"update_context replace called for task {self.id}; keys={list(updates.keys())}")
                except Exception:
                    pass
                self.context = updates
        except Exception:
            # In case of unexpected error, log stack for forensic analysis but preserve behavior
            try:
                logger.exception(f"Failed to update context for task {self.id}: {traceback.format_exc()}")
            except Exception:
                pass
    
    def add_to_history(self, history_type: str, data: Dict[str, Any]) -> None:
        """Add entry to interaction history in context"""
        context = self.get_context()
        if "interaction_history" not in context:
            context["interaction_history"] = []
        
        history_entry = {
            "type": history_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        context["interaction_history"].append(history_entry)
        self.context = context

    def refresh(self, session=None) -> None:
        """
        Backwards-compatible refresh() method used by tests.
        If a session is provided, use it to refresh the instance from DB.
        Otherwise, no-op (tests call refresh() to ensure up-to-date instance).
        """
        if session is not None:
            try:
                session.refresh(self)
            except Exception:
                # best-effort; ignore refresh failures in test environment
                pass
    
    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, description={self.description[:50]}...)>"

