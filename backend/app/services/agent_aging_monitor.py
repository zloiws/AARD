"""
Agent Aging Monitor Service
Monitors agent performance degradation and creates update tasks
"""
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.core.logging_config import LoggingConfig
from app.models.agent import Agent, AgentStatus, AgentHealthStatus
from app.models.task import Task, TaskStatus
from app.services.artifact_version_service import ArtifactVersionService

logger = LoggingConfig.get_logger(__name__)


class AgentAgingMonitor:
    """
    Service for monitoring agent aging and degradation
    
    Detects:
    - Performance degradation (decreasing success_rate, increasing error_rate)
    - Increasing execution times
    - Decreasing usage (agents not used for long time)
    - Health status degradation
    
    Actions:
    - Creates tasks for agent updates
    - Marks agents for deprecation
    - Suggests improvements based on metrics
    """
    
    def __init__(self, db: Session):
        """
        Initialize Agent Aging Monitor
        
        Args:
            db: Database session
        """
        self.db = db
        self.version_service = ArtifactVersionService(db)
    
    def check_agent_aging(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Check if agent is showing signs of aging/degradation
        
        Args:
            agent_id: Agent ID to check
            
        Returns:
            Dictionary with aging analysis results
        """
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent.status != AgentStatus.ACTIVE.value:
            return {
                "is_aging": False,
                "reason": f"Agent is not active (status: {agent.status})",
                "recommendations": []
            }
        
        analysis = {
            "agent_id": str(agent_id),
            "agent_name": agent.name,
            "version": agent.version,
            "is_aging": False,
            "issues": [],
            "severity": "none",  # none, low, medium, high, critical
            "recommendations": [],
            "metrics": {}
        }
        
        # 1. Check performance metrics degradation
        performance_issues = self._check_performance_degradation(agent)
        if performance_issues:
            analysis["issues"].extend(performance_issues["issues"])
            analysis["metrics"]["performance"] = performance_issues["metrics"]
            if performance_issues["severity"] in ["medium", "high", "critical"]:
                analysis["is_aging"] = True
                analysis["severity"] = performance_issues["severity"]
        
        # 2. Check version comparison (if versioning is available)
        version_issues = self._check_version_degradation(agent)
        if version_issues:
            analysis["issues"].extend(version_issues["issues"])
            analysis["metrics"]["version"] = version_issues["metrics"]
            if version_issues["severity"] in ["medium", "high", "critical"]:
                analysis["is_aging"] = True
                if self._get_severity_level(version_issues["severity"]) > self._get_severity_level(analysis["severity"]):
                    analysis["severity"] = version_issues["severity"]
        
        # 3. Check usage patterns
        usage_issues = self._check_usage_patterns(agent)
        if usage_issues:
            analysis["issues"].extend(usage_issues["issues"])
            analysis["metrics"]["usage"] = usage_issues["metrics"]
            if usage_issues["severity"] == "high":
                analysis["is_aging"] = True
                if self._get_severity_level(usage_issues["severity"]) > self._get_severity_level(analysis["severity"]):
                    analysis["severity"] = usage_issues["severity"]
        
        # 4. Check health status
        health_issues = self._check_health_status(agent)
        if health_issues:
            analysis["issues"].extend(health_issues["issues"])
            analysis["metrics"]["health"] = health_issues["metrics"]
            if health_issues["severity"] in ["medium", "high", "critical"]:
                analysis["is_aging"] = True
                if self._get_severity_level(health_issues["severity"]) > self._get_severity_level(analysis["severity"]):
                    analysis["severity"] = health_issues["severity"]
        
        # Generate recommendations
        if analysis["is_aging"]:
            analysis["recommendations"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _check_performance_degradation(self, agent: Agent) -> Optional[Dict[str, Any]]:
        """Check if agent performance is degrading"""
        issues = []
        metrics = {}
        severity = "none"
        
        # Calculate current success rate
        if agent.total_tasks_executed > 0:
            current_success_rate = (agent.successful_tasks / agent.total_tasks_executed) * 100
            metrics["current_success_rate"] = current_success_rate
            metrics["total_tasks"] = agent.total_tasks_executed
            metrics["successful_tasks"] = agent.successful_tasks
            metrics["failed_tasks"] = agent.failed_tasks
            
            # Check if success rate is below threshold
            if current_success_rate < 70:  # Below 70% is concerning
                issues.append({
                    "type": "low_success_rate",
                    "message": f"Success rate is {current_success_rate:.1f}% (below 70% threshold)",
                    "severity": "high" if current_success_rate < 50 else "medium"
                })
                severity = "high" if current_success_rate < 50 else "medium"
            
            # Check if error rate is increasing
            error_rate = (agent.failed_tasks / agent.total_tasks_executed) * 100
            metrics["error_rate"] = error_rate
            if error_rate > 30:  # More than 30% errors
                issues.append({
                    "type": "high_error_rate",
                    "message": f"Error rate is {error_rate:.1f}% (above 30% threshold)",
                    "severity": "high" if error_rate > 50 else "medium"
                })
                if severity == "none" or (error_rate > 50 and severity != "critical"):
                    severity = "high" if error_rate > 50 else "medium"
        
        # Check execution time
        if agent.average_execution_time:
            metrics["avg_execution_time"] = agent.average_execution_time
            # If execution time is very high (more than 60 seconds average), it's concerning
            if agent.average_execution_time > 60:
                issues.append({
                    "type": "slow_execution",
                    "message": f"Average execution time is {agent.average_execution_time}s (above 60s threshold)",
                    "severity": "medium"
                })
                if severity == "none":
                    severity = "medium"
        
        if issues:
            return {
                "issues": issues,
                "metrics": metrics,
                "severity": severity
            }
        
        return None
    
    def _check_version_degradation(self, agent: Agent) -> Optional[Dict[str, Any]]:
        """Check if agent version is showing degradation compared to previous versions"""
        issues = []
        metrics = {}
        severity = "none"
        
        try:
            # Try to get artifact version for this agent
            # Note: This assumes agent is also stored as Artifact
            from app.models.artifact import Artifact
            
            artifact = self.db.query(Artifact).filter(
                and_(
                    Artifact.type == "agent",
                    Artifact.name == agent.name
                )
            ).first()
            
            if artifact:
                # Compare current version with previous
                should_rollback, reason = self.version_service.should_rollback(
                    artifact_id=artifact.id,
                    current_version=artifact.version,
                    threshold_percent=15.0
                )
                
                if should_rollback:
                    issues.append({
                        "type": "version_degradation",
                        "message": f"Version degradation detected: {reason}",
                        "severity": "high"
                    })
                    severity = "high"
                    metrics["rollback_recommended"] = True
                    metrics["rollback_reason"] = reason
        except Exception as e:
            logger.debug(f"Could not check version degradation: {e}")
        
        if issues:
            return {
                "issues": issues,
                "metrics": metrics,
                "severity": severity
            }
        
        return None
    
    def _check_usage_patterns(self, agent: Agent) -> Optional[Dict[str, Any]]:
        """Check agent usage patterns for signs of aging"""
        issues = []
        metrics = {}
        severity = "none"
        
        # Check last usage
        if agent.last_used_at:
            days_since_last_use = (datetime.now(timezone.utc) - agent.last_used_at).days
            metrics["days_since_last_use"] = days_since_last_use
            
            if days_since_last_use > 90:  # Not used for 90+ days
                issues.append({
                    "type": "low_usage",
                    "message": f"Agent not used for {days_since_last_use} days",
                    "severity": "low"
                })
                severity = "low"
        else:
            # Never used
            days_since_creation = (datetime.now(timezone.utc) - agent.created_at).days
            if days_since_creation > 30:
                issues.append({
                    "type": "never_used",
                    "message": f"Agent created {days_since_creation} days ago but never used",
                    "severity": "medium"
                })
                severity = "medium"
                metrics["days_since_creation"] = days_since_creation
        
        # Check age of agent
        agent_age_days = (datetime.now(timezone.utc) - agent.created_at).days
        metrics["agent_age_days"] = agent_age_days
        
        if agent_age_days > 365:  # Older than 1 year
            issues.append({
                "type": "old_agent",
                "message": f"Agent is {agent_age_days} days old (may need update)",
                "severity": "low"
            })
            if severity == "none":
                severity = "low"
        
        if issues:
            return {
                "issues": issues,
                "metrics": metrics,
                "severity": severity
            }
        
        return None
    
    def _check_health_status(self, agent: Agent) -> Optional[Dict[str, Any]]:
        """Check agent health status"""
        issues = []
        metrics = {}
        severity = "none"
        
        metrics["health_status"] = agent.health_status
        metrics["last_health_check"] = agent.last_health_check.isoformat() if agent.last_health_check else None
        
        if agent.health_status == AgentHealthStatus.UNHEALTHY.value:
            issues.append({
                "type": "unhealthy",
                "message": "Agent health status is UNHEALTHY",
                "severity": "critical"
            })
            severity = "critical"
        elif agent.health_status == AgentHealthStatus.DEGRADED.value:
            issues.append({
                "type": "degraded",
                "message": "Agent health status is DEGRADED",
                "severity": "high"
            })
            severity = "high"
        
        # Check if health check is stale
        if agent.last_health_check:
            days_since_health_check = (datetime.now(timezone.utc) - agent.last_health_check).days
            if days_since_health_check > 7:  # No health check for 7+ days
                issues.append({
                    "type": "stale_health_check",
                    "message": f"Last health check was {days_since_health_check} days ago",
                    "severity": "medium"
                })
                if severity == "none":
                    severity = "medium"
                metrics["days_since_health_check"] = days_since_health_check
        
        if issues:
            return {
                "issues": issues,
                "metrics": metrics,
                "severity": severity
            }
        
        return None
    
    def _get_severity_level(self, severity: str) -> int:
        """Get numeric level for severity comparison"""
        levels = {
            "none": 0,
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4
        }
        return levels.get(severity, 0)
    
    def _generate_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        for issue in analysis["issues"]:
            issue_type = issue.get("type")
            
            if issue_type == "low_success_rate":
                recommendations.append(
                    f"Update agent prompt/system_prompt to improve success rate. "
                    f"Current: {analysis['metrics'].get('performance', {}).get('current_success_rate', 0):.1f}%"
                )
            elif issue_type == "high_error_rate":
                recommendations.append(
                    "Review and fix common error patterns. Consider adding error handling or validation."
                )
            elif issue_type == "slow_execution":
                recommendations.append(
                    "Optimize agent execution. Consider caching, parallelization, or model selection."
                )
            elif issue_type == "version_degradation":
                recommendations.append(
                    "Rollback to previous version or update agent to fix degradation."
                )
            elif issue_type == "low_usage" or issue_type == "never_used":
                recommendations.append(
                    "Consider deprecating agent if not needed, or update to make it more useful."
                )
            elif issue_type == "old_agent":
                recommendations.append(
                    "Review and update agent to match current requirements and best practices."
                )
            elif issue_type == "unhealthy" or issue_type == "degraded":
                recommendations.append(
                    "Investigate health issues. Check agent endpoint, dependencies, and configuration."
                )
        
        if not recommendations:
            recommendations.append("Monitor agent closely for further degradation.")
        
        return recommendations
    
    def create_update_task(self, agent_id: UUID, analysis: Dict[str, Any]) -> Optional[Task]:
        """
        Create a task for updating an aging agent
        
        Args:
            agent_id: Agent ID
            analysis: Aging analysis results
            
        Returns:
            Created Task or None if task already exists
        """
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Check if update task already exists
        existing_task = self.db.query(Task).filter(
            and_(
                Task.description.like(f"%Update agent {agent.name}%"),
                Task.status.in_([TaskStatus.PENDING, TaskStatus.PENDING_APPROVAL, TaskStatus.IN_PROGRESS])
            )
        ).first()
        
        if existing_task:
            logger.info(f"Update task already exists for agent {agent.name}: {existing_task.id}")
            return existing_task
        
        # Create update task
        task_description = f"Update agent {agent.name} (version {agent.version})"
        
        # Add details from analysis
        details = []
        if analysis.get("issues"):
            details.append("Issues detected:")
            for issue in analysis["issues"][:3]:  # Limit to 3 issues
                details.append(f"- {issue.get('message')}")
        
        if analysis.get("recommendations"):
            details.append("\nRecommendations:")
            for rec in analysis["recommendations"][:3]:  # Limit to 3 recommendations
                details.append(f"- {rec}")
        
        full_description = f"{task_description}\n\n{chr(10).join(details)}"
        
        task = Task(
            description=full_description,
            status=TaskStatus.PENDING,
            priority=7 if analysis.get("severity") in ["high", "critical"] else 5,
            created_by="system",
            created_by_role="system",
            autonomy_level=2,  # Requires plan approval
            context={
                "type": "agent_update",
                "agent_id": str(agent_id),
                "agent_name": agent.name,
                "current_version": agent.version,
                "aging_analysis": analysis,
                "created_by_monitor": True
            }
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(
            f"Created update task {task.id} for aging agent {agent.name}",
            extra={
                "task_id": str(task.id),
                "agent_id": str(agent_id),
                "severity": analysis.get("severity")
            }
        )
        
        return task
    
    def monitor_all_agents(self, min_severity: str = "medium") -> Dict[str, Any]:
        """
        Monitor all active agents for aging
        
        Args:
            min_severity: Minimum severity to create update tasks (none, low, medium, high, critical)
            
        Returns:
            Monitoring results
        """
        active_agents = self.db.query(Agent).filter(
            Agent.status == AgentStatus.ACTIVE.value
        ).all()
        
        results = {
            "total_agents": len(active_agents),
            "aging_agents": [],
            "tasks_created": 0,
            "severity_distribution": {
                "none": 0,
                "low": 0,
                "medium": 0,
                "high": 0,
                "critical": 0
            }
        }
        
        severity_level = self._get_severity_level(min_severity)
        
        for agent in active_agents:
            try:
                analysis = self.check_agent_aging(agent.id)
                
                if analysis.get("is_aging"):
                    results["aging_agents"].append({
                        "agent_id": str(agent.id),
                        "agent_name": agent.name,
                        "severity": analysis.get("severity"),
                        "issues_count": len(analysis.get("issues", []))
                    })
                    
                    # Update severity distribution
                    severity = analysis.get("severity", "none")
                    results["severity_distribution"][severity] = results["severity_distribution"].get(severity, 0) + 1
                    
                    # Create update task if severity is high enough
                    if self._get_severity_level(severity) >= severity_level:
                        task = self.create_update_task(agent.id, analysis)
                        if task:
                            results["tasks_created"] += 1
            except Exception as e:
                logger.error(
                    f"Error monitoring agent {agent.id}: {e}",
                    exc_info=True,
                    extra={"agent_id": str(agent.id)}
                )
        
        logger.info(
            f"Agent aging monitoring completed: {results['tasks_created']} tasks created for {len(results['aging_agents'])} aging agents",
            extra=results
        )
        
        return results

