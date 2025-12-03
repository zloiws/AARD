"""
Feedback Learning Service for learning from human feedback
Extracts patterns from approval/rejection feedback and applies them to future decisions
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.approval import ApprovalRequest
from app.models.learning_pattern import LearningPattern, PatternType
from app.services.meta_learning_service import MetaLearningService

logger = LoggingConfig.get_logger(__name__)


class FeedbackLearningService:
    """
    Service for learning from human feedback:
    - Extracts patterns from approval/rejection feedback
    - Applies learned patterns to future decisions
    - Improves planning based on feedback
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize Feedback Learning Service
        
        Args:
            db: Database session (optional)
        """
        self.db = db or SessionLocal()
        self.meta_learning = MetaLearningService(db)
    
    def learn_from_approval_feedback(
        self,
        approval: ApprovalRequest,
        human_feedback: Optional[str] = None
    ) -> Optional[LearningPattern]:
        """
        Learn from approval feedback and extract patterns
        
        Args:
            approval: ApprovalRequest instance
            human_feedback: Optional human feedback text
            
        Returns:
            LearningPattern if pattern was extracted, None otherwise
        """
        try:
            # Extract feedback from approval
            feedback_text = human_feedback or approval.human_feedback or ""
            
            # Get approval decision
            is_approved = approval.status == "approved"
            
            # Extract patterns based on approval type
            pattern = None
            
            if approval.request_type == "plan_approval":
                pattern = self._extract_plan_pattern(approval, is_approved, feedback_text)
            elif approval.request_type == "new_artifact":
                pattern = self._extract_artifact_pattern(approval, is_approved, feedback_text)
            elif approval.request_type == "prompt_change":
                pattern = self._extract_prompt_pattern(approval, is_approved, feedback_text)
            
            if pattern:
                # Save pattern
                learning_pattern = LearningPattern(
                    pattern_type=pattern["type"],
                    name=pattern["name"],
                    description=pattern.get("description"),
                    pattern_data=pattern["data"],
                    success_rate=1.0 if is_approved else 0.0,  # Approved = successful pattern
                    usage_count=1,
                    total_executions=1,
                    successful_executions=1 if is_approved else 0,
                    task_category=pattern.get("task_category")
                )
                
                self.db.add(learning_pattern)
                self.db.commit()
                self.db.refresh(learning_pattern)
                
                logger.info(
                    f"Extracted pattern from approval feedback: {pattern['name']}",
                    extra={
                        "approval_id": str(approval.id),
                        "pattern_type": pattern["type"],
                        "approved": is_approved
                    }
                )
                
                return learning_pattern
            
            return None
            
        except Exception as e:
            logger.error(f"Error learning from approval feedback: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def _extract_plan_pattern(
        self,
        approval: ApprovalRequest,
        is_approved: bool,
        feedback: str
    ) -> Optional[Dict[str, Any]]:
        """Extract pattern from plan approval"""
        try:
            request_data = approval.request_data or {}
            plan_id = request_data.get("plan_id")
            
            if not plan_id:
                return None
            
            # Get plan details
            from app.models.plan import Plan
            plan = self.db.query(Plan).filter(Plan.id == UUID(plan_id)).first()
            
            if not plan:
                return None
            
            # Extract pattern data
            pattern_data = {
                "plan_id": plan_id,
                "goal": plan.goal[:200] if plan.goal else "",
                "total_steps": len(plan.steps) if isinstance(plan.steps, list) else 0,
                "risk_assessment": approval.risk_assessment or {},
                "feedback": feedback,
                "approved": is_approved
            }
            
            # Extract key information from feedback
            if feedback:
                # Look for keywords
                feedback_lower = feedback.lower()
                if "too complex" in feedback_lower or "simplify" in feedback_lower:
                    pattern_data["suggestion"] = "simplify"
                elif "missing" in feedback_lower or "add" in feedback_lower:
                    pattern_data["suggestion"] = "add_steps"
                elif "good" in feedback_lower or "excellent" in feedback_lower:
                    pattern_data["suggestion"] = "maintain_approach"
            
            return {
                "type": PatternType.STRATEGY.value,
                "name": f"Plan Pattern: {plan.goal[:50] if plan.goal else 'Unknown'}",
                "description": f"Pattern extracted from plan approval (approved: {is_approved})",
                "data": pattern_data,
                "task_category": self._categorize_task(plan.goal)
            }
            
        except Exception as e:
            logger.error(f"Error extracting plan pattern: {e}", exc_info=True)
            return None
    
    def _extract_artifact_pattern(
        self,
        approval: ApprovalRequest,
        is_approved: bool,
        feedback: str
    ) -> Optional[Dict[str, Any]]:
        """Extract pattern from artifact approval"""
        try:
            request_data = approval.request_data or {}
            
            pattern_data = {
                "artifact_id": str(approval.artifact_id) if approval.artifact_id else None,
                "artifact_type": request_data.get("type"),
                "feedback": feedback,
                "approved": is_approved
            }
            
            return {
                "type": PatternType.TOOL_SELECTION.value,
                "name": f"Artifact Pattern: {request_data.get('name', 'Unknown')}",
                "description": f"Pattern extracted from artifact approval (approved: {is_approved})",
                "data": pattern_data
            }
            
        except Exception as e:
            logger.error(f"Error extracting artifact pattern: {e}", exc_info=True)
            return None
    
    def _extract_prompt_pattern(
        self,
        approval: ApprovalRequest,
        is_approved: bool,
        feedback: str
    ) -> Optional[Dict[str, Any]]:
        """Extract pattern from prompt change approval"""
        try:
            request_data = approval.request_data or {}
            
            pattern_data = {
                "prompt_id": str(approval.prompt_id) if approval.prompt_id else None,
                "prompt_text": request_data.get("prompt", "")[:500],
                "feedback": feedback,
                "approved": is_approved
            }
            
            # Extract keywords from feedback
            if feedback:
                feedback_lower = feedback.lower()
                keywords = []
                if "clear" in feedback_lower:
                    keywords.append("clarity")
                if "specific" in feedback_lower:
                    keywords.append("specificity")
                if "concise" in feedback_lower:
                    keywords.append("conciseness")
                pattern_data["improvement_keywords"] = keywords
            
            return {
                "type": PatternType.PROMPT.value,
                "name": f"Prompt Pattern: {request_data.get('name', 'Unknown')}",
                "description": f"Pattern extracted from prompt approval (approved: {is_approved})",
                "data": pattern_data
            }
            
        except Exception as e:
            logger.error(f"Error extracting prompt pattern: {e}", exc_info=True)
            return None
    
    def _categorize_task(self, task_description: str) -> str:
        """Categorize task based on description"""
        if not task_description:
            return "general"
        
        desc_lower = task_description.lower()
        
        if any(word in desc_lower for word in ["code", "program", "function", "script"]):
            return "code_generation"
        elif any(word in desc_lower for word in ["data", "analyze", "process", "transform"]):
            return "data_processing"
        elif any(word in desc_lower for word in ["test", "validate", "check"]):
            return "testing"
        elif any(word in desc_lower for word in ["deploy", "release", "publish"]):
            return "deployment"
        else:
            return "general"
    
    def apply_learned_patterns(
        self,
        task_description: str,
        task_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply learned patterns to a task description
        
        Args:
            task_description: Task description
            task_category: Optional task category
            
        Returns:
            Dictionary with pattern-based recommendations
        """
        try:
            if not task_category:
                task_category = self._categorize_task(task_description)
            
            # Get relevant patterns
            patterns = self.meta_learning.get_patterns_for_task(
                task_category=task_category
            )
            
            # Filter for high-success patterns
            successful_patterns = [p for p in patterns if p.success_rate > 0.7]
            
            recommendations = {
                "task_category": task_category,
                "patterns_found": len(successful_patterns),
                "recommendations": []
            }
            
            # Extract recommendations from patterns
            for pattern in successful_patterns[:5]:  # Top 5 patterns
                pattern_data = pattern.pattern_data or {}
                suggestion = pattern_data.get("suggestion")
                
                if suggestion:
                    recommendations["recommendations"].append({
                        "pattern_id": str(pattern.id),
                        "pattern_name": pattern.name,
                        "suggestion": suggestion,
                        "success_rate": pattern.success_rate,
                        "usage_count": pattern.usage_count
                    })
            
            logger.debug(
                f"Applied {len(recommendations['recommendations'])} learned patterns",
                extra={"task_category": task_category}
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error applying learned patterns: {e}", exc_info=True)
            return {
                "task_category": task_category or "general",
                "patterns_found": 0,
                "recommendations": []
            }
    
    def extract_improvements_from_feedback(self, feedback: str) -> Dict[str, Any]:
        """
        Extract improvement suggestions from feedback text
        
        Args:
            feedback: Human feedback text
            
        Returns:
            Dictionary with extracted improvements
        """
        try:
            if not feedback:
                return {"improvements": [], "keywords": []}
            
            feedback_lower = feedback.lower()
            improvements = []
            keywords = []
            
            # Extract improvement suggestions
            if "simplify" in feedback_lower or "too complex" in feedback_lower:
                improvements.append("Simplify the approach")
                keywords.append("simplicity")
            
            if "add" in feedback_lower and ("step" in feedback_lower or "check" in feedback_lower):
                improvements.append("Add more validation steps")
                keywords.append("validation")
            
            if "missing" in feedback_lower:
                improvements.append("Include missing information")
                keywords.append("completeness")
            
            if "clear" in feedback_lower or "unclear" in feedback_lower:
                improvements.append("Improve clarity")
                keywords.append("clarity")
            
            if "specific" in feedback_lower or "vague" in feedback_lower:
                improvements.append("Be more specific")
                keywords.append("specificity")
            
            if "time" in feedback_lower and ("long" in feedback_lower or "slow" in feedback_lower):
                improvements.append("Optimize for performance")
                keywords.append("performance")
            
            return {
                "improvements": improvements,
                "keywords": keywords,
                "feedback_length": len(feedback)
            }
            
        except Exception as e:
            logger.error(f"Error extracting improvements from feedback: {e}", exc_info=True)
            return {"improvements": [], "keywords": []}
    
    def get_feedback_statistics(
        self,
        agent_id: Optional[UUID] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get statistics about feedback learning
        
        Args:
            agent_id: Optional agent ID
            time_range_days: Number of days to analyze
            
        Returns:
            Dictionary with feedback statistics
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=time_range_days)
            
            query = self.db.query(ApprovalRequest).filter(
                ApprovalRequest.created_at >= cutoff_date
            )
            
            if agent_id:
                # Filter by plans executed by this agent
                from app.models.plan import Plan
                plan_ids = self.db.query(Plan.id).filter(
                    Plan.agent_metadata.contains({"agent_id": str(agent_id)})
                ).subquery()
                query = query.filter(ApprovalRequest.plan_id.in_(plan_ids))
            
            approvals = query.all()
            
            total = len(approvals)
            approved = sum(1 for a in approvals if a.status == "approved")
            rejected = sum(1 for a in approvals if a.status == "rejected")
            with_feedback = sum(1 for a in approvals if a.human_feedback)
            
            # Get patterns extracted from feedback
            patterns = self.db.query(LearningPattern).filter(
                LearningPattern.created_at >= cutoff_date
            ).count()
            
            return {
                "total_approvals": total,
                "approved": approved,
                "rejected": rejected,
                "with_feedback": with_feedback,
                "patterns_extracted": patterns,
                "feedback_rate": with_feedback / total if total > 0 else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting feedback statistics: {e}", exc_info=True)
            return {
                "total_approvals": 0,
                "approved": 0,
                "rejected": 0,
                "with_feedback": 0,
                "patterns_extracted": 0,
                "feedback_rate": 0.0
            }

