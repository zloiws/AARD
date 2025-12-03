"""
Planning Metrics Service for tracking plan quality and performance
Provides metrics and statistics for plan generation and execution
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.plan import Plan, PlanStatus
from app.models.trace import ExecutionTrace
from app.models.task import Task, TaskStatus

logger = LoggingConfig.get_logger(__name__)


class PlanningMetricsService:
    """
    Service for tracking planning metrics:
    - Plan quality scores
    - Execution success rates
    - Planning statistics
    - Performance metrics
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize Planning Metrics Service
        
        Args:
            db: Database session (optional)
        """
        self.db = db or SessionLocal()
    
    def calculate_plan_quality_score(self, plan: Plan) -> float:
        """
        Calculate quality score for a plan (0.0 to 1.0)
        
        Factors:
        - Number of steps (optimal range)
        - Step dependencies (complexity)
        - Estimated vs actual duration
        - Execution success rate
        
        Args:
            plan: Plan instance
            
        Returns:
            Quality score (0.0 to 1.0)
        """
        try:
            score = 0.0
            
            if not plan:
                return 0.0
            
            steps = plan.steps if isinstance(plan.steps, list) else []
            num_steps = len(steps)
            
            # Factor 1: Step count (optimal: 3-7 steps) - 30%
            if 3 <= num_steps <= 7:
                score += 0.3
            elif 2 <= num_steps <= 10:
                score += 0.2
            elif num_steps > 0:
                score += 0.1
            
            # Factor 2: Step structure (has required fields) - 20%
            well_structured = 0
            for step in steps:
                if isinstance(step, dict):
                    if all(key in step for key in ["step_id", "description", "type"]):
                        well_structured += 1
            
            if num_steps > 0:
                structure_ratio = well_structured / num_steps
                score += 0.2 * structure_ratio
            
            # Factor 3: Execution success rate - 30%
            traces = self.db.query(ExecutionTrace).filter(
                ExecutionTrace.plan_id == plan.id
            ).all()
            
            if traces:
                successful = sum(1 for t in traces if t.status == "success")
                success_rate = successful / len(traces)
                score += 0.3 * success_rate
            else:
                # No execution yet - neutral score
                score += 0.15
            
            # Factor 4: Duration accuracy (if available) - 20%
            if plan.estimated_duration and plan.actual_duration:
                estimated = plan.estimated_duration
                actual = plan.actual_duration
                
                if estimated > 0:
                    accuracy = 1.0 - min(1.0, abs(actual - estimated) / estimated)
                    score += 0.2 * accuracy
                else:
                    score += 0.1
            else:
                score += 0.1  # No duration data - neutral
            
            # Normalize to 0.0-1.0
            score = max(0.0, min(1.0, score))
            
            logger.debug(
                f"Calculated quality score for plan {plan.id}",
                extra={
                    "plan_id": str(plan.id),
                    "quality_score": score,
                    "num_steps": num_steps
                }
            )
            
            return score
            
        except Exception as e:
            logger.error(f"Error calculating plan quality score: {e}", exc_info=True)
            return 0.0
    
    def track_plan_execution_success(
        self,
        plan_id: UUID,
        success: bool,
        execution_time_ms: Optional[int] = None
    ) -> None:
        """
        Track plan execution success/failure
        
        Args:
            plan_id: Plan ID
            success: Whether execution was successful
            execution_time_ms: Optional execution time in milliseconds
        """
        try:
            plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                logger.warning(f"Plan {plan_id} not found for tracking")
                return
            
            # Update plan status
            if success:
                if plan.status != PlanStatus.COMPLETED.value:
                    plan.status = PlanStatus.COMPLETED.value
            else:
                if plan.status != PlanStatus.FAILED.value:
                    plan.status = PlanStatus.FAILED.value
            
            # Update actual duration if provided
            if execution_time_ms:
                plan.actual_duration = execution_time_ms // 1000  # Convert to seconds
            
            self.db.commit()
            
            logger.debug(
                f"Tracked execution for plan {plan_id}",
                extra={
                    "plan_id": str(plan_id),
                    "success": success,
                    "execution_time_ms": execution_time_ms
                }
            )
            
        except Exception as e:
            logger.error(f"Error tracking plan execution: {e}", exc_info=True)
            self.db.rollback()
    
    def get_planning_statistics(
        self,
        agent_id: Optional[UUID] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get planning statistics for an agent or system-wide
        
        Args:
            agent_id: Optional agent ID
            time_range_days: Number of days to analyze
            
        Returns:
            Dictionary with planning statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)
            
            # Query plans
            query = self.db.query(Plan).filter(Plan.created_at >= cutoff_date)
            
            if agent_id:
                # Filter by agent (if agent metadata is stored in plan)
                # This would require plan.agent_metadata or similar
                pass  # TODO: Implement agent filtering if needed
            
            plans = query.all()
            
            total_plans = len(plans)
            completed = sum(1 for p in plans if p.status == PlanStatus.COMPLETED.value)
            failed = sum(1 for p in plans if p.status == PlanStatus.FAILED.value)
            executing = sum(1 for p in plans if p.status == PlanStatus.EXECUTING.value)
            approved = sum(1 for p in plans if p.status == PlanStatus.APPROVED.value)
            
            # Calculate average quality scores
            quality_scores = [self.calculate_plan_quality_score(p) for p in plans]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            # Calculate average steps per plan
            total_steps = sum(
                len(p.steps) if isinstance(p.steps, list) else 0
                for p in plans
            )
            avg_steps = total_steps / total_plans if total_plans > 0 else 0.0
            
            # Calculate success rate
            success_rate = completed / total_plans if total_plans > 0 else 0.0
            
            # Calculate average duration (for completed plans)
            completed_plans = [p for p in plans if p.actual_duration]
            avg_duration = (
                sum(p.actual_duration for p in completed_plans) / len(completed_plans)
                if completed_plans else None
            )
            
            return {
                "total_plans": total_plans,
                "completed": completed,
                "failed": failed,
                "executing": executing,
                "approved": approved,
                "success_rate": success_rate,
                "average_quality_score": avg_quality,
                "average_steps_per_plan": avg_steps,
                "average_duration_seconds": avg_duration,
                "time_range_days": time_range_days
            }
            
        except Exception as e:
            logger.error(f"Error getting planning statistics: {e}", exc_info=True)
            return {
                "total_plans": 0,
                "completed": 0,
                "failed": 0,
                "executing": 0,
                "approved": 0,
                "success_rate": 0.0,
                "average_quality_score": 0.0,
                "average_steps_per_plan": 0.0,
                "average_duration_seconds": None,
                "time_range_days": time_range_days
            }
    
    def get_plan_quality_breakdown(self, plan_id: UUID) -> Dict[str, Any]:
        """
        Get detailed quality breakdown for a plan
        
        Args:
            plan_id: Plan ID
            
        Returns:
            Dictionary with quality breakdown
        """
        try:
            plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
            if not plan:
                return {"error": "Plan not found"}
            
            steps = plan.steps if isinstance(plan.steps, list) else []
            
            # Get execution traces
            traces = self.db.query(ExecutionTrace).filter(
                ExecutionTrace.plan_id == plan_id
            ).all()
            
            breakdown = {
                "plan_id": str(plan_id),
                "overall_quality_score": self.calculate_plan_quality_score(plan),
                "factors": {
                    "step_count": len(steps),
                    "step_count_score": 0.0,
                    "structure_score": 0.0,
                    "execution_success_rate": 0.0,
                    "duration_accuracy": 0.0
                },
                "execution_stats": {
                    "total_executions": len(traces),
                    "successful": sum(1 for t in traces if t.status == "success"),
                    "failed": sum(1 for t in traces if t.status == "error")
                }
            }
            
            # Calculate factor scores
            num_steps = len(steps)
            if 3 <= num_steps <= 7:
                breakdown["factors"]["step_count_score"] = 0.3
            elif 2 <= num_steps <= 10:
                breakdown["factors"]["step_count_score"] = 0.2
            elif num_steps > 0:
                breakdown["factors"]["step_count_score"] = 0.1
            
            # Structure score
            if num_steps > 0:
                well_structured = sum(
                    1 for step in steps
                    if isinstance(step, dict) and all(
                        key in step for key in ["step_id", "description", "type"]
                    )
                )
                breakdown["factors"]["structure_score"] = (well_structured / num_steps) * 0.2
            
            # Execution success rate
            if traces:
                successful = sum(1 for t in traces if t.status == "success")
                breakdown["factors"]["execution_success_rate"] = (successful / len(traces)) * 0.3
                breakdown["execution_stats"]["success_rate"] = successful / len(traces)
            
            # Duration accuracy
            if plan.estimated_duration and plan.actual_duration:
                estimated = plan.estimated_duration
                actual = plan.actual_duration
                if estimated > 0:
                    accuracy = 1.0 - min(1.0, abs(actual - estimated) / estimated)
                    breakdown["factors"]["duration_accuracy"] = accuracy * 0.2
            
            return breakdown
            
        except Exception as e:
            logger.error(f"Error getting plan quality breakdown: {e}", exc_info=True)
            return {"error": str(e)}

