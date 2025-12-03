"""
Adaptive Approval Service for intelligent approval decisions
Determines if approval is required based on risk level, agent trust score, and task complexity
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.agent import Agent
from app.models.plan import Plan
from app.models.trace import ExecutionTrace
from app.models.approval import ApprovalRequest

logger = LoggingConfig.get_logger(__name__)


class AdaptiveApprovalService:
    """
    Service for adaptive approval decisions based on:
    - Agent trust score (history of successful executions)
    - Task risk level (complexity, type of operations)
    - Plan complexity (number of steps, dependencies)
    """
    
    # Thresholds for approval decisions
    TRUST_SCORE_THRESHOLD = 0.8  # Agents with trust > 0.8 may skip approval for low-risk tasks
    HIGH_RISK_THRESHOLD = 0.7  # Tasks with risk > 0.7 always require approval
    MEDIUM_RISK_THRESHOLD = 0.4  # Tasks with risk > 0.4 require approval if trust < threshold
    
    # Minimum number of executions for trust calculation
    MIN_EXECUTIONS_FOR_TRUST = 5
    
    def __init__(self, db: Session = None):
        """
        Initialize Adaptive Approval Service
        
        Args:
            db: Database session (optional)
        """
        self.db = db or SessionLocal()
    
    def should_require_approval(
        self,
        plan: Plan,
        agent_id: Optional[UUID] = None,
        task_risk_level: Optional[float] = None,
        override_risk: bool = False
    ) -> tuple[bool, Dict[str, Any]]:
        """
        Determine if approval is required for a plan
        
        Args:
            plan: Plan to evaluate
            agent_id: Optional agent ID (if plan is executed by specific agent)
            task_risk_level: Optional pre-calculated risk level (0.0 to 1.0)
            override_risk: If True, always require approval regardless of calculations
            
        Returns:
            Tuple of (requires_approval, decision_metadata)
        """
        try:
            if override_risk:
                return True, {
                    "reason": "override_risk",
                    "message": "Approval required due to override"
                }
            
            # Calculate risk level if not provided
            if task_risk_level is None:
                task_risk_level = self.calculate_task_risk_level(
                    plan.goal,
                    plan.steps if isinstance(plan.steps, list) else []
                )
            
            # Calculate agent trust score if agent is specified
            agent_trust_score = None
            if agent_id:
                agent_trust_score = self.calculate_agent_trust_score(agent_id)
            
            # Decision logic
            requires_approval = False
            reason = "low_risk_high_trust"
            
            # Always require approval for high-risk tasks
            if task_risk_level >= self.HIGH_RISK_THRESHOLD:
                requires_approval = True
                reason = "high_risk"
            
            # Require approval for medium-risk tasks if agent trust is low
            elif task_risk_level >= self.MEDIUM_RISK_THRESHOLD:
                if agent_trust_score is None or agent_trust_score < self.TRUST_SCORE_THRESHOLD:
                    requires_approval = True
                    reason = "medium_risk_low_trust"
                else:
                    requires_approval = False
                    reason = "medium_risk_high_trust"
            
            # Low-risk tasks: require approval only if agent trust is very low
            else:
                if agent_trust_score is not None and agent_trust_score < 0.5:
                    requires_approval = True
                    reason = "low_risk_very_low_trust"
                else:
                    requires_approval = False
                    reason = "low_risk_acceptable_trust"
            
            decision_metadata = {
                "requires_approval": requires_approval,
                "reason": reason,
                "task_risk_level": task_risk_level,
                "agent_trust_score": agent_trust_score,
                "thresholds": {
                    "high_risk": self.HIGH_RISK_THRESHOLD,
                    "medium_risk": self.MEDIUM_RISK_THRESHOLD,
                    "trust_threshold": self.TRUST_SCORE_THRESHOLD
                }
            }
            
            logger.info(
                f"Approval decision: {reason}",
                extra={
                    "plan_id": str(plan.id),
                    "agent_id": str(agent_id) if agent_id else None,
                    "requires_approval": requires_approval,
                    "task_risk_level": task_risk_level,
                    "agent_trust_score": agent_trust_score
                }
            )
            
            return requires_approval, decision_metadata
            
        except Exception as e:
            logger.error(f"Error determining approval requirement: {e}", exc_info=True)
            # Default to requiring approval on error (safe default)
            return True, {
                "reason": "error",
                "message": f"Error calculating approval requirement: {str(e)}"
            }
    
    def calculate_agent_trust_score(self, agent_id: UUID) -> float:
        """
        Calculate trust score for an agent based on execution history
        
        Trust score is calculated based on:
        - Success rate (weight: 0.6)
        - Number of successful executions (weight: 0.2)
        - Recent performance (last 30 days) (weight: 0.2)
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Trust score (0.0 to 1.0)
        """
        try:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return 0.0  # Unknown agent = no trust
            
            # Base trust from agent metrics
            total_tasks = agent.total_tasks_executed or 0
            successful_tasks = agent.successful_tasks or 0
            failed_tasks = agent.failed_tasks or 0
            
            # Need minimum executions for reliable trust score
            if total_tasks < self.MIN_EXECUTIONS_FOR_TRUST:
                # New agent: low trust, but not zero
                base_trust = 0.3 if total_tasks > 0 else 0.1
                logger.debug(
                    f"Agent {agent.name} has insufficient history ({total_tasks} tasks), using base trust: {base_trust}",
                    extra={"agent_id": str(agent_id), "total_tasks": total_tasks}
                )
                return base_trust
            
            # Calculate success rate
            if total_tasks > 0:
                success_rate = successful_tasks / total_tasks
            else:
                success_rate = 0.0
            
            # Calculate recent performance (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            recent_traces = self.db.query(ExecutionTrace).filter(
                and_(
                    ExecutionTrace.agent_id == agent_id,
                    ExecutionTrace.start_time >= thirty_days_ago,
                    ExecutionTrace.status.isnot(None)
                )
            ).all()
            
            recent_successful = sum(1 for t in recent_traces if t.status == "success")
            recent_total = len(recent_traces)
            
            recent_performance = 0.5  # Default if no recent data
            if recent_total > 0:
                recent_performance = recent_successful / recent_total
            
            # Weighted trust score
            trust_score = (
                success_rate * 0.6 +  # Overall success rate (60%)
                min(1.0, total_tasks / 100.0) * 0.2 +  # Experience factor (20%)
                recent_performance * 0.2  # Recent performance (20%)
            )
            
            # Normalize to 0.0-1.0
            trust_score = max(0.0, min(1.0, trust_score))
            
            logger.debug(
                f"Calculated trust score for agent {agent.name}",
                extra={
                    "agent_id": str(agent_id),
                    "trust_score": trust_score,
                    "success_rate": success_rate,
                    "total_tasks": total_tasks,
                    "recent_performance": recent_performance
                }
            )
            
            return trust_score
            
        except Exception as e:
            logger.error(f"Error calculating agent trust score: {e}", exc_info=True)
            return 0.0  # Default to no trust on error
    
    def detect_critical_steps(
        self,
        steps: List[Dict[str, Any]],
        task_description: str = ""
    ) -> Dict[str, Any]:
        """
        Detect critical steps that require mandatory approval
        
        Critical steps include:
        - Creating new agents or tools
        - Modifying existing artifacts (agents, tools, prompts)
        - Accessing protected data/APIs
        - System-level operations
        
        Args:
            steps: List of plan steps
            task_description: Optional task description for context
            
        Returns:
            Dictionary with critical step information:
            {
                "has_critical_steps": bool,
                "critical_steps": List[Dict],
                "critical_types": List[str],
                "requires_mandatory_approval": bool
            }
        """
        try:
            critical_steps = []
            critical_types = set()
            
            if not steps:
                steps = []
            
            # Keywords and patterns for critical operations
            critical_patterns = {
                "create_agent": [
                    "create.*agent", "new.*agent", "add.*agent",
                    "register.*agent", "define.*agent"
                ],
                "modify_agent": [
                    "modify.*agent", "update.*agent", "change.*agent",
                    "edit.*agent", "alter.*agent"
                ],
                "create_tool": [
                    "create.*tool", "new.*tool", "add.*tool",
                    "register.*tool", "define.*tool"
                ],
                "modify_tool": [
                    "modify.*tool", "update.*tool", "change.*tool",
                    "edit.*tool", "alter.*tool"
                ],
                "modify_artifact": [
                    "modify.*artifact", "update.*artifact", "change.*artifact",
                    "edit.*artifact", "alter.*artifact", "delete.*artifact"
                ],
                "system_operation": [
                    "system.*command", "shell.*command", "execute.*system",
                    "root.*access", "admin.*privilege"
                ],
                "protected_data": [
                    "access.*database", "modify.*database", "delete.*data",
                    "access.*api.*key", "access.*secret", "access.*credential"
                ]
            }
            
            # Check each step
            for i, step in enumerate(steps):
                step_text = ""
                if isinstance(step, dict):
                    step_text = " ".join([
                        str(step.get("description", "")),
                        str(step.get("action", "")),
                        str(step.get("step_description", "")),
                        str(step.get("name", ""))
                    ]).lower()
                else:
                    step_text = str(step).lower()
                
                # Check against critical patterns
                for critical_type, patterns in critical_patterns.items():
                    for pattern in patterns:
                        import re
                        if re.search(pattern, step_text, re.IGNORECASE):
                            critical_steps.append({
                                "step_index": i,
                                "step": step,
                                "critical_type": critical_type,
                                "matched_pattern": pattern
                            })
                            critical_types.add(critical_type)
                            break
            
            # Also check task description
            task_lower = task_description.lower() if task_description else ""
            for critical_type, patterns in critical_patterns.items():
                for pattern in patterns:
                    import re
                    if re.search(pattern, task_lower, re.IGNORECASE):
                        critical_types.add(critical_type)
                        break
            
            # Determine if mandatory approval is required
            # Mandatory approval for: creating/modifying agents, tools, system operations
            mandatory_types = {
                "create_agent", "modify_agent", "create_tool", "modify_tool",
                "system_operation", "protected_data"
            }
            requires_mandatory_approval = bool(critical_types & mandatory_types)
            
            result = {
                "has_critical_steps": len(critical_steps) > 0 or len(critical_types) > 0,
                "critical_steps": critical_steps,
                "critical_types": list(critical_types),
                "requires_mandatory_approval": requires_mandatory_approval
            }
            
            logger.info(
                "Detected critical steps",
                extra={
                    "has_critical_steps": result["has_critical_steps"],
                    "critical_types": result["critical_types"],
                    "requires_mandatory_approval": requires_mandatory_approval,
                    "num_critical_steps": len(critical_steps)
                }
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting critical steps: {e}", exc_info=True)
            # Default to requiring approval on error (safe default)
            return {
                "has_critical_steps": True,
                "critical_steps": [],
                "critical_types": ["error"],
                "requires_mandatory_approval": True
            }
    
    def calculate_task_risk_level(
        self,
        task_description: str,
        steps: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate risk level for a task/plan
        
        Risk factors:
        - Number of steps (more steps = higher risk)
        - High-risk operations (file operations, database writes, etc.)
        - Approval-required steps
        - Dependencies between steps
        - Estimated duration
        
        Args:
            task_description: Task description
            steps: List of plan steps
            
        Returns:
            Risk level (0.0 to 1.0)
        """
        try:
            risk_score = 0.0
            
            if not steps:
                steps = []
            
            # Factor 1: Number of steps (0.0 to 0.3)
            num_steps = len(steps)
            if num_steps > 10:
                risk_score += 0.3
            elif num_steps > 5:
                risk_score += 0.2
            elif num_steps > 2:
                risk_score += 0.1
            
            # Factor 2: High-risk operations (0.0 to 0.4)
            high_risk_keywords = [
                "delete", "remove", "drop", "destroy", "format",
                "write", "modify", "update", "change", "alter",
                "execute", "run", "system", "shell", "command"
            ]
            
            task_lower = task_description.lower()
            high_risk_count = sum(1 for keyword in high_risk_keywords if keyword in task_lower)
            
            if high_risk_count >= 3:
                risk_score += 0.4
            elif high_risk_count >= 2:
                risk_score += 0.3
            elif high_risk_count >= 1:
                risk_score += 0.2
            
            # Factor 3: Steps requiring approval (0.0 to 0.2)
            approval_steps = sum(1 for step in steps if step.get("approval_required", False))
            if approval_steps > 0:
                risk_score += min(0.2, approval_steps * 0.1)
            
            # Factor 4: High-risk step types (0.0 to 0.1)
            high_risk_step_types = ["validation", "approval"]
            high_risk_steps = sum(1 for step in steps if step.get("type") in high_risk_step_types)
            if high_risk_steps > 0:
                risk_score += min(0.1, high_risk_steps * 0.05)
            
            # Factor 5: Complex dependencies (0.0 to 0.1)
            steps_with_deps = sum(1 for step in steps if step.get("dependencies") and len(step.get("dependencies", [])) > 0)
            if steps_with_deps > 3:
                risk_score += 0.1
            elif steps_with_deps > 1:
                risk_score += 0.05
            
            # Normalize to 0.0-1.0
            risk_score = max(0.0, min(1.0, risk_score))
            
            logger.debug(
                "Calculated task risk level",
                extra={
                    "risk_score": risk_score,
                    "num_steps": num_steps,
                    "high_risk_keywords": high_risk_count,
                    "approval_steps": approval_steps
                }
            )
            
            return risk_score
            
        except Exception as e:
            logger.error(f"Error calculating task risk level: {e}", exc_info=True)
            return 0.5  # Default to medium risk on error
    
    def get_approval_statistics(self, agent_id: Optional[UUID] = None) -> Dict[str, Any]:
        """
        Get approval statistics for an agent or system-wide
        
        Args:
            agent_id: Optional agent ID for agent-specific statistics
            
        Returns:
            Dictionary with approval statistics
        """
        try:
            # Query approval requests
            query = self.db.query(ApprovalRequest)
            
            if agent_id:
                # Filter by plans executed by this agent
                # This would require joining with execution traces
                pass  # TODO: Implement agent-specific filtering
            
            total_requests = query.count()
            pending = query.filter(ApprovalRequest.status == "pending").count()
            approved = query.filter(ApprovalRequest.status == "approved").count()
            rejected = query.filter(ApprovalRequest.status == "rejected").count()
            
            # Calculate approval rate
            total_decided = approved + rejected
            approval_rate = approved / total_decided if total_decided > 0 else 0.0
            
            return {
                "total_requests": total_requests,
                "pending": pending,
                "approved": approved,
                "rejected": rejected,
                "approval_rate": approval_rate
            }
            
        except Exception as e:
            logger.error(f"Error getting approval statistics: {e}", exc_info=True)
            return {
                "total_requests": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "approval_rate": 0.0
            }

