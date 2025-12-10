"""
Interactive Execution Service for human oversight during execution
Allows pausing execution for clarification and applying human corrections
"""
from typing import Dict, Any, Optional, Callable, Awaitable
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from enum import Enum

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class ExecutionState(str, Enum):
    """Execution state for interactive control"""
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_CLARIFICATION = "waiting_clarification"
    WAITING_CORRECTION = "waiting_correction"
    RESUMED = "resumed"
    COMPLETED = "completed"
    FAILED = "failed"


class InteractiveExecutionService:
    """
    Service for interactive execution with human oversight:
    - Pause execution for clarification
    - Apply human corrections
    - Resume execution after feedback
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize Interactive Execution Service
        
        Args:
            db: Database session (optional)
        """
        self.db = db or SessionLocal()
        self._execution_states: Dict[UUID, Dict[str, Any]] = {}
    
    async def execute_with_human_oversight(
        self,
        step: Dict[str, Any],
        plan_id: UUID,
        human_feedback_callback: Optional[Callable[[str, Dict[str, Any]], Awaitable[Optional[str]]]] = None
    ) -> Dict[str, Any]:
        """
        Execute step with human oversight capability
        
        Args:
            step: Step definition
            plan_id: Plan ID
            human_feedback_callback: Optional callback for human feedback
            
        Returns:
            Execution result
        """
        try:
            step_id = step.get("step_id", "unknown")
            
            # Initialize execution state
            execution_state = {
                "step_id": step_id,
                "plan_id": str(plan_id),
                "state": ExecutionState.RUNNING.value,
                "started_at": datetime.now(timezone.utc),
                "paused_at": None,
                "clarification_question": None,
                "human_feedback": None,
                "correction": None
            }
            self._execution_states[plan_id] = execution_state
            
            logger.info(
                f"Starting interactive execution for step {step_id}",
                extra={"step_id": step_id, "plan_id": str(plan_id)}
            )
            
            # Check if step requires clarification
            if step.get("requires_clarification", False):
                question = step.get("clarification_question", "Do you want to proceed with this step?")
                
                execution_state["state"] = ExecutionState.WAITING_CLARIFICATION.value
                execution_state["clarification_question"] = question
                execution_state["paused_at"] = datetime.now(timezone.utc)
                
                if human_feedback_callback:
                    feedback = await human_feedback_callback(question, step)
                    if feedback:
                        execution_state["human_feedback"] = feedback
                        if feedback.lower() in ["no", "stop", "cancel"]:
                            return {
                                "status": "cancelled",
                                "message": "Execution cancelled by human",
                                "step_id": step_id
                            }
                
                execution_state["state"] = ExecutionState.RESUMED.value
            
            # Execute step (placeholder - actual execution would be done by ExecutionService)
            result = {
                "status": "completed",
                "step_id": step_id,
                "output": "Step executed successfully",
                "execution_state": execution_state
            }
            
            execution_state["state"] = ExecutionState.COMPLETED.value
            
            return result
            
        except Exception as e:
            logger.error(f"Error in interactive execution: {e}", exc_info=True)
            if plan_id in self._execution_states:
                self._execution_states[plan_id]["state"] = ExecutionState.FAILED.value
            return {
                "status": "failed",
                "error": str(e),
                "step_id": step.get("step_id", "unknown")
            }
    
    def pause_for_clarification(
        self,
        plan_id: UUID,
        step_id: str,
        question: str
    ) -> Dict[str, Any]:
        """
        Pause execution for clarification
        
        Args:
            plan_id: Plan ID
            step_id: Step ID
            question: Question for human
            
        Returns:
            Pause state information
        """
        try:
            if plan_id not in self._execution_states:
                self._execution_states[plan_id] = {
                    "step_id": step_id,
                    "plan_id": str(plan_id),
                    "state": ExecutionState.WAITING_CLARIFICATION.value,
                    "paused_at": datetime.now(timezone.utc),
                    "clarification_question": question
                }
            else:
                self._execution_states[plan_id]["state"] = ExecutionState.WAITING_CLARIFICATION.value
                self._execution_states[plan_id]["paused_at"] = datetime.now(timezone.utc)
                self._execution_states[plan_id]["clarification_question"] = question
            
            logger.info(
                f"Paused execution for clarification: {question}",
                extra={"plan_id": str(plan_id), "step_id": step_id}
            )
            
            return {
                "state": ExecutionState.WAITING_CLARIFICATION.value,
                "question": question,
                "paused_at": self._execution_states[plan_id]["paused_at"].isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error pausing for clarification: {e}", exc_info=True)
            return {"error": str(e)}
    
    def apply_human_correction(
        self,
        plan_id: UUID,
        step_id: str,
        correction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply human correction to step
        
        Args:
            plan_id: Plan ID
            step_id: Step ID
            correction: Correction data (updated step definition, etc.)
            
        Returns:
            Correction application result
        """
        try:
            if plan_id not in self._execution_states:
                return {"error": "No execution state found for this plan"}
            
            execution_state = self._execution_states[plan_id]
            execution_state["correction"] = correction
            execution_state["state"] = ExecutionState.WAITING_CORRECTION.value
            
            logger.info(
                f"Applied human correction to step {step_id}",
                extra={
                    "plan_id": str(plan_id),
                    "step_id": step_id,
                    "correction": correction
                }
            )
            
            return {
                "status": "correction_applied",
                "step_id": step_id,
                "correction": correction
            }
            
        except Exception as e:
            logger.error(f"Error applying human correction: {e}", exc_info=True)
            return {"error": str(e)}
    
    def resume_execution(
        self,
        plan_id: UUID,
        feedback: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Resume execution after pause
        
        Args:
            plan_id: Plan ID
            feedback: Optional human feedback
            
        Returns:
            Resume result
        """
        try:
            if plan_id not in self._execution_states:
                return {"error": "No execution state found for this plan"}
            
            execution_state = self._execution_states[plan_id]
            execution_state["state"] = ExecutionState.RESUMED.value
            if feedback:
                execution_state["human_feedback"] = feedback
            
            logger.info(
                f"Resumed execution for plan {plan_id}",
                extra={"plan_id": str(plan_id), "feedback": feedback}
            )
            
            return {
                "status": "resumed",
                "state": ExecutionState.RESUMED.value
            }
            
        except Exception as e:
            logger.error(f"Error resuming execution: {e}", exc_info=True)
            return {"error": str(e)}
    
    def get_execution_state(self, plan_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get current execution state
        
        Args:
            plan_id: Plan ID
            
        Returns:
            Execution state or None
        """
        return self._execution_states.get(plan_id)
    
    def clear_execution_state(self, plan_id: UUID) -> bool:
        """
        Clear execution state for a plan
        
        Args:
            plan_id: Plan ID
            
        Returns:
            True if cleared, False if not found
        """
        if plan_id in self._execution_states:
            del self._execution_states[plan_id]
            return True
        return False

