"""
Plan Evaluation Service for A/B testing
Evaluates plans based on multiple criteria and ranks them
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.plan import Plan
from app.models.approval import ApprovalRequest, ApprovalRequestType

logger = LoggingConfig.get_logger(__name__)


class PlanEvaluationResult:
    """Result of plan evaluation"""
    
    def __init__(
        self,
        plan_id: UUID,
        plan: Plan,
        scores: Dict[str, float],
        total_score: float,
        ranking: int = 0,
        recommendations: List[str] = None
    ):
        self.plan_id = plan_id
        self.plan = plan
        self.scores = scores  # Individual criterion scores
        self.total_score = total_score  # Weighted total score
        self.ranking = ranking  # Rank among evaluated plans (1 = best)
        self.recommendations = recommendations or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert evaluation result to dictionary"""
        return {
            "plan_id": str(self.plan_id),
            "goal": self.plan.goal,
            "scores": self.scores,
            "total_score": self.total_score,
            "ranking": self.ranking,
            "recommendations": self.recommendations,
            "estimated_duration": self.plan.estimated_duration,
            "steps_count": len(self.plan.steps) if self.plan.steps else 0,
            "strategy": self.plan.strategy.get("alternative_strategy") if isinstance(self.plan.strategy, dict) else None
        }


class PlanEvaluationService:
    """
    Service for evaluating and ranking plans based on multiple criteria:
    - Expected execution time
    - Number of approval points
    - Risk level
    - Efficiency (minimal number of steps)
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize Plan Evaluation Service
        
        Args:
            db: Database session (optional)
        """
        self.db = db or SessionLocal()
    
    def evaluate_plan(
        self,
        plan: Plan,
        weights: Optional[Dict[str, float]] = None
    ) -> PlanEvaluationResult:
        """
        Evaluate a single plan based on multiple criteria
        
        Args:
            plan: Plan to evaluate
            weights: Optional weights for criteria (default: equal weights)
            
        Returns:
            PlanEvaluationResult with scores and recommendations
        """
        if weights is None:
            weights = {
                "execution_time": 0.25,
                "approval_points": 0.20,
                "risk_level": 0.25,
                "efficiency": 0.30
            }
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        
        # Evaluate each criterion
        execution_time_score = self._evaluate_execution_time(plan)
        approval_points_score = self._evaluate_approval_points(plan)
        risk_level_score = self._evaluate_risk_level(plan)
        efficiency_score = self._evaluate_efficiency(plan)
        
        scores = {
            "execution_time": execution_time_score,
            "approval_points": approval_points_score,
            "risk_level": risk_level_score,
            "efficiency": efficiency_score
        }
        
        # Calculate weighted total score
        total_score = (
            execution_time_score * weights.get("execution_time", 0.25) +
            approval_points_score * weights.get("approval_points", 0.20) +
            risk_level_score * weights.get("risk_level", 0.25) +
            efficiency_score * weights.get("efficiency", 0.30)
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(plan, scores)
        
        return PlanEvaluationResult(
            plan_id=plan.id,
            plan=plan,
            scores=scores,
            total_score=total_score,
            recommendations=recommendations
        )
    
    def evaluate_plans(
        self,
        plans: List[Plan],
        weights: Optional[Dict[str, float]] = None
    ) -> List[PlanEvaluationResult]:
        """
        Evaluate multiple plans and rank them
        
        Args:
            plans: List of plans to evaluate
            weights: Optional weights for criteria
            
        Returns:
            List of PlanEvaluationResult, sorted by total_score (descending)
        """
        results = []
        
        for plan in plans:
            try:
                result = self.evaluate_plan(plan, weights)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate plan {plan.id}: {e}", exc_info=True)
        
        # Rank plans by total score (highest = best)
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        # Assign rankings
        for i, result in enumerate(results, 1):
            result.ranking = i
        
        return results
    
    def _evaluate_execution_time(self, plan: Plan) -> float:
        """
        Evaluate plan based on expected execution time
        
        Lower execution time = higher score (0.0 to 1.0)
        
        Args:
            plan: Plan to evaluate
            
        Returns:
            Score from 0.0 (worst) to 1.0 (best)
        """
        estimated_duration = plan.estimated_duration
        
        if estimated_duration is None:
            # If no estimate, calculate from steps
            steps = plan.steps if isinstance(plan.steps, list) else []
            estimated_duration = sum(
                step.get("estimated_time", 600) for step in steps if isinstance(step, dict)
            )
        
        if estimated_duration is None or estimated_duration <= 0:
            return 0.5  # Neutral score if no duration available
        
        # Score based on duration (shorter = better)
        # Normalize: 0-3600 seconds (1 hour) = 1.0, 3600-7200 = 0.5, >7200 = 0.0
        if estimated_duration <= 3600:  # 1 hour
            return 1.0
        elif estimated_duration <= 7200:  # 2 hours
            return 1.0 - ((estimated_duration - 3600) / 3600) * 0.5
        else:  # > 2 hours
            # Exponential decay for longer durations
            excess = estimated_duration - 7200
            return max(0.0, 0.5 * (0.9 ** (excess / 3600)))
    
    def _evaluate_approval_points(self, plan: Plan) -> float:
        """
        Evaluate plan based on number of approval points
        
        Fewer approval points = higher score (0.0 to 1.0)
        
        Args:
            plan: Plan to evaluate
            
        Returns:
            Score from 0.0 (worst) to 1.0 (best)
        """
        # Count approval requests for this plan
        approval_count = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.plan_id == plan.id
        ).count()
        
        # Also estimate based on steps that might require approval
        steps = plan.steps if isinstance(plan.steps, list) else []
        estimated_approvals = 0
        
        for step in steps:
            if isinstance(step, dict):
                step_type = step.get("type", "").lower()
                # Steps that typically require approval
                if step_type in ["deployment", "production", "database", "security", "payment"]:
                    estimated_approvals += 1
                # Check if step explicitly requires approval
                if step.get("requires_approval", False):
                    estimated_approvals += 1
        
        total_approval_points = approval_count + estimated_approvals
        
        # Score: 0 approvals = 1.0, 1-2 = 0.8, 3-4 = 0.5, 5+ = 0.2
        if total_approval_points == 0:
            return 1.0
        elif total_approval_points <= 2:
            return 1.0 - (total_approval_points * 0.1)
        elif total_approval_points <= 4:
            return 0.8 - ((total_approval_points - 2) * 0.15)
        else:
            return max(0.2, 0.5 - ((total_approval_points - 4) * 0.1))
    
    def _evaluate_risk_level(self, plan: Plan) -> float:
        """
        Evaluate plan based on risk level
        
        Lower risk = higher score (0.0 to 1.0)
        
        Args:
            plan: Plan to evaluate
            
        Returns:
            Score from 0.0 (worst) to 1.0 (best)
        """
        # Extract risk information from strategy
        strategy = plan.strategy if isinstance(plan.strategy, dict) else {}
        
        # Check alternative strategy risk tolerance
        risk_tolerance = strategy.get("alternative_risk_tolerance", "medium").lower()
        if risk_tolerance == "low":
            base_score = 0.9
        elif risk_tolerance == "medium":
            base_score = 0.7
        elif risk_tolerance == "high":
            base_score = 0.5
        else:
            base_score = 0.7
        
        # Analyze steps for risk indicators
        steps = plan.steps if isinstance(plan.steps, list) else []
        risk_factors = 0
        
        for step in steps:
            if isinstance(step, dict):
                step_type = step.get("type", "").lower()
                description = step.get("description", "").lower()
                
                # High-risk step types
                if step_type in ["deployment", "production", "database", "security", "payment", "delete"]:
                    risk_factors += 1
                
                # Risk keywords in description
                risk_keywords = ["delete", "drop", "remove", "destroy", "critical", "production", "live"]
                if any(keyword in description for keyword in risk_keywords):
                    risk_factors += 0.5
        
        # Adjust score based on risk factors
        risk_penalty = min(0.3, risk_factors * 0.1)
        final_score = max(0.0, base_score - risk_penalty)
        
        return final_score
    
    def _evaluate_efficiency(self, plan: Plan) -> float:
        """
        Evaluate plan based on efficiency (minimal number of steps)
        
        Fewer steps = higher score, but too few steps = lower score (optimal range)
        
        Args:
            plan: Plan to evaluate
            
        Returns:
            Score from 0.0 (worst) to 1.0 (best)
        """
        steps = plan.steps if isinstance(plan.steps, list) else []
        step_count = len(steps)
        
        if step_count == 0:
            return 0.0
        
        # Optimal step count: 3-7 steps
        # Score distribution:
        # 1-2 steps: 0.6 (too few, might miss important steps)
        # 3-5 steps: 1.0 (optimal)
        # 6-7 steps: 0.9 (good)
        # 8-10 steps: 0.7 (acceptable)
        # 11-15 steps: 0.5 (too many)
        # 16+ steps: 0.3 (excessive)
        
        if step_count <= 2:
            return 0.6
        elif step_count <= 5:
            return 1.0
        elif step_count <= 7:
            return 0.9
        elif step_count <= 10:
            return 0.7
        elif step_count <= 15:
            return 0.5
        else:
            return 0.3
    
    def _generate_recommendations(
        self,
        plan: Plan,
        scores: Dict[str, float]
    ) -> List[str]:
        """
        Generate recommendations based on evaluation scores
        
        Args:
            plan: Plan that was evaluated
            scores: Individual criterion scores
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Execution time recommendations
        if scores["execution_time"] < 0.5:
            recommendations.append("Consider optimizing execution time - plan may take too long")
        
        # Approval points recommendations
        if scores["approval_points"] < 0.5:
            recommendations.append("High number of approval points may slow down execution")
        
        # Risk level recommendations
        if scores["risk_level"] < 0.5:
            recommendations.append("High risk detected - consider adding safety checks or breaking into smaller steps")
        
        # Efficiency recommendations
        step_count = len(plan.steps) if plan.steps else 0
        if scores["efficiency"] < 0.5:
            if step_count > 10:
                recommendations.append(f"Too many steps ({step_count}) - consider consolidating or removing redundant steps")
            elif step_count <= 2:
                recommendations.append(f"Too few steps ({step_count}) - plan may be missing important steps")
        elif step_count > 10:
            # Even if efficiency score is OK, warn about too many steps
            recommendations.append(f"Many steps ({step_count}) - consider if all are necessary")
        
        # Overall recommendations
        total_score = sum(scores.values()) / len(scores)
        if total_score < 0.6:
            recommendations.append("Overall plan quality is below optimal - consider reviewing all aspects")
        
        return recommendations
    
    def compare_plans(
        self,
        plans: List[Plan],
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Compare multiple plans and provide detailed comparison
        
        Args:
            plans: List of plans to compare
            weights: Optional weights for criteria
            
        Returns:
            Dictionary with comparison results
        """
        if not plans:
            return {
                "plans": [],
                "best_plan": None,
                "comparison": {}
            }
        
        # Evaluate all plans
        results = self.evaluate_plans(plans, weights)
        
        # Find best plan
        best_result = results[0] if results else None
        
        # Build comparison matrix
        comparison = {
            "execution_time": {},
            "approval_points": {},
            "risk_level": {},
            "efficiency": {},
            "total_score": {}
        }
        
        for result in results:
            plan_id_str = str(result.plan_id)
            comparison["execution_time"][plan_id_str] = result.scores["execution_time"]
            comparison["approval_points"][plan_id_str] = result.scores["approval_points"]
            comparison["risk_level"][plan_id_str] = result.scores["risk_level"]
            comparison["efficiency"][plan_id_str] = result.scores["efficiency"]
            comparison["total_score"][plan_id_str] = result.total_score
        
        return {
            "plans": [result.to_dict() for result in results],
            "best_plan": best_result.to_dict() if best_result else None,
            "comparison": comparison,
            "weights": weights or {
                "execution_time": 0.25,
                "approval_points": 0.20,
                "risk_level": 0.25,
                "efficiency": 0.30
            }
        }

