"""
Service for managing checkpoints and rollback
"""
import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.tracing import get_current_trace_id
from app.models.artifact import Artifact
from app.models.checkpoint import Checkpoint
from app.models.plan import Plan
from app.models.task import Task
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class CheckpointService:
    """Service for managing checkpoints and rollback"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_checkpoint(
        self,
        entity_type: str,
        entity_id: UUID,
        state_data: Dict[str, Any],
        reason: Optional[str] = None,
        created_by: Optional[str] = None,
        request_id: Optional[UUID] = None,
    ) -> Checkpoint:
        """
        Create a checkpoint for an entity
        
        Args:
            entity_type: Type of entity (plan, task, artifact, etc.)
            entity_id: Entity ID
            state_data: Full state data to save
            reason: Reason for creating checkpoint
            created_by: User or system that created checkpoint
            request_id: Optional request log ID
            
        Returns:
            Created Checkpoint
        """
        # Calculate hash of state data
        state_json = json.dumps(state_data, sort_keys=True, default=str)
        state_hash = hashlib.sha256(state_json.encode()).hexdigest()
        
        # Get trace ID
        trace_id = get_current_trace_id()
        
        checkpoint = Checkpoint(
            entity_type=entity_type,
            entity_id=entity_id,
            state_data=state_data,
            state_hash=state_hash,
            reason=reason or "Automatic checkpoint",
            created_by=created_by or "system",
            request_id=request_id,
            trace_id=trace_id,
        )
        
        self.db.add(checkpoint)
        self.db.commit()
        self.db.refresh(checkpoint)
        
        logger.debug(
            f"Created checkpoint for {entity_type}:{entity_id}",
            extra={
                "checkpoint_id": str(checkpoint.id),
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "reason": reason,
            }
        )
        
        return checkpoint
    
    def get_checkpoint(self, checkpoint_id: UUID) -> Optional[Checkpoint]:
        """Get a checkpoint by ID"""
        return self.db.query(Checkpoint).filter(Checkpoint.id == checkpoint_id).first()
    
    def get_latest_checkpoint(
        self,
        entity_type: str,
        entity_id: UUID
    ) -> Optional[Checkpoint]:
        """
        Get the latest checkpoint for an entity
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            
        Returns:
            Latest Checkpoint or None
        """
        return self.db.query(Checkpoint).filter(
            and_(
                Checkpoint.entity_type == entity_type,
                Checkpoint.entity_id == entity_id
            )
        ).order_by(desc(Checkpoint.created_at)).first()
    
    def list_checkpoints(
        self,
        entity_type: str,
        entity_id: UUID,
        limit: int = 10
    ) -> List[Checkpoint]:
        """
        List checkpoints for an entity
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            limit: Maximum number of checkpoints
            
        Returns:
            List of Checkpoints
        """
        return self.db.query(Checkpoint).filter(
            and_(
                Checkpoint.entity_type == entity_type,
                Checkpoint.entity_id == entity_id
            )
        ).order_by(desc(Checkpoint.created_at)).limit(limit).all()
    
    def restore_checkpoint(
        self,
        checkpoint_id: UUID
    ) -> Dict[str, Any]:
        """
        Restore state from a checkpoint
        
        Args:
            checkpoint_id: Checkpoint ID
            
        Returns:
            Restored state data
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"Checkpoint {checkpoint_id} not found")
        
        # Verify hash integrity
        state_json = json.dumps(checkpoint.state_data, sort_keys=True, default=str)
        calculated_hash = hashlib.sha256(state_json.encode()).hexdigest()
        
        if checkpoint.state_hash and calculated_hash != checkpoint.state_hash:
            raise ValueError(f"Checkpoint {checkpoint_id} integrity check failed")
        
        logger.info(
            f"Restored checkpoint {checkpoint_id}",
            extra={
                "checkpoint_id": str(checkpoint_id),
                "entity_type": checkpoint.entity_type,
                "entity_id": str(checkpoint.entity_id),
            }
        )
        
        return checkpoint.state_data
    
    def rollback_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        checkpoint_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Rollback an entity to a checkpoint
        
        Args:
            entity_type: Type of entity
            entity_id: Entity ID
            checkpoint_id: Optional checkpoint ID (uses latest if not provided)
            
        Returns:
            Restored state data
        """
        if checkpoint_id:
            checkpoint = self.get_checkpoint(checkpoint_id)
            if not checkpoint:
                raise ValueError(f"Checkpoint {checkpoint_id} not found")
            if checkpoint.entity_type != entity_type or checkpoint.entity_id != entity_id:
                raise ValueError(f"Checkpoint does not match entity")
        else:
            checkpoint = self.get_latest_checkpoint(entity_type, entity_id)
            if not checkpoint:
                raise ValueError(f"No checkpoint found for {entity_type}:{entity_id}")
        
        # Restore state
        state_data = self.restore_checkpoint(checkpoint.id)
        
        # Apply to entity based on type
        if entity_type == "plan":
            self._restore_plan(entity_id, state_data)
        elif entity_type == "task":
            self._restore_task(entity_id, state_data)
        elif entity_type == "artifact":
            self._restore_artifact(entity_id, state_data)
        else:
            logger.warning(f"Unknown entity type for rollback: {entity_type}")
        
        logger.info(
            f"Rolled back {entity_type}:{entity_id} to checkpoint {checkpoint.id}",
            extra={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "checkpoint_id": str(checkpoint.id),
            }
        )
        
        return state_data
    
    def _restore_plan(self, plan_id: UUID, state_data: Dict[str, Any]):
        """Restore plan from state data"""
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Restore plan fields
        if "status" in state_data:
            plan.status = state_data["status"]
        if "current_step" in state_data:
            plan.current_step = state_data["current_step"]
        if "steps" in state_data:
            plan.steps = state_data["steps"]
        if "strategy" in state_data:
            plan.strategy = state_data["strategy"]
        
        self.db.commit()
        self.db.refresh(plan)
    
    def _restore_task(self, task_id: UUID, state_data: Dict[str, Any]):
        """Restore task from state data"""
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        # Restore task fields
        if "status" in state_data:
            task.status = state_data["status"]
        if "description" in state_data:
            task.description = state_data["description"]
        if "priority" in state_data:
            task.priority = state_data["priority"]
        
        self.db.commit()
        self.db.refresh(task)
    
    def _restore_artifact(self, artifact_id: UUID, state_data: Dict[str, Any]):
        """Restore artifact from state data"""
        artifact = self.db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if not artifact:
            raise ValueError(f"Artifact {artifact_id} not found")
        
        # Restore artifact fields
        if "status" in state_data:
            artifact.status = state_data["status"]
        if "code" in state_data:
            artifact.code = state_data["code"]
        if "description" in state_data:
            artifact.description = state_data["description"]
        
        self.db.commit()
        self.db.refresh(artifact)
    
    def create_plan_checkpoint(
        self,
        plan: Plan,
        reason: Optional[str] = None
    ) -> Checkpoint:
        """
        Create a checkpoint for a plan
        
        Args:
            plan: Plan object
            reason: Reason for checkpoint
            
        Returns:
            Created Checkpoint
        """
        state_data = {
            "id": str(plan.id),
            "task_id": str(plan.task_id),
            "version": plan.version,
            "goal": plan.goal,
            "strategy": plan.strategy,
            "steps": plan.steps,
            "alternatives": plan.alternatives,
            "status": plan.status,
            "current_step": plan.current_step,
            "estimated_duration": plan.estimated_duration,
            "actual_duration": plan.actual_duration,
        }
        
        return self.create_checkpoint(
            entity_type="plan",
            entity_id=plan.id,
            state_data=state_data,
            reason=reason or f"Checkpoint before step {plan.current_step}",
        )
    
    def create_task_checkpoint(
        self,
        task: Task,
        reason: Optional[str] = None
    ) -> Checkpoint:
        """
        Create a checkpoint for a task
        
        Args:
            task: Task object
            reason: Reason for checkpoint
            
        Returns:
            Created Checkpoint
        """
        state_data = {
            "id": str(task.id),
            "description": task.description,
            "status": task.status.value if hasattr(task.status, 'value') else str(task.status),
            "priority": task.priority,
            "plan_id": str(task.plan_id) if task.plan_id else None,
        }
        
        return self.create_checkpoint(
            entity_type="task",
            entity_id=task.id,
            state_data=state_data,
            reason=reason or "Task checkpoint",
        )

