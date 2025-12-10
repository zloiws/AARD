"""
Agent Evolution Service
Self-improvement system for agents through metric analysis and A/B testing
"""
import re
import json
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging_config import LoggingConfig
from app.models.agent import Agent, AgentStatus
from app.models.artifact import Artifact, ArtifactType
from app.models.evolution import EvolutionHistory, EntityType, ChangeType, TriggerType, Feedback
from app.models.agent_experiment import AgentExperiment, ExperimentStatus
from app.services.agent_aging_monitor import AgentAgingMonitor
from app.services.agent_experiment_service import AgentExperimentService
from app.services.artifact_version_service import ArtifactVersionService
from app.services.artifact_generator import ArtifactGenerator
from app.core.ollama_client import OllamaClient

logger = LoggingConfig.get_logger(__name__)


class AgentEvolutionService:
    """
    Service for self-improvement of agents through:
    - Metric analysis (from AgentAgingMonitor)
    - A/B testing (via AgentExperimentService)
    - Automatic improvement application
    - Feedback integration
    """
    
    def __init__(self, db: Session, ollama_client: OllamaClient):
        """
        Initialize Agent Evolution Service
        
        Args:
            db: Database session
            ollama_client: Ollama client for LLM operations
        """
        self.db = db
        self.ollama_client = ollama_client
        self.aging_monitor = AgentAgingMonitor(db)
        self.experiment_service = AgentExperimentService(db)
        self.version_service = ArtifactVersionService(db)
        self.artifact_generator = ArtifactGenerator(db, ollama_client)
    
    async def improve_agent(
        self,
        agent_id: UUID,
        improvement_reason: Optional[str] = None,
        target_metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Improve an agent based on metrics and create improved version
        
        Args:
            agent_id: Agent ID to improve
            improvement_reason: Reason for improvement (if None, will analyze)
            target_metrics: Target metrics to achieve
            
        Returns:
            Dictionary with improvement results
        """
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # 1. Analyze current state
        if not improvement_reason:
            aging_analysis = self.aging_monitor.check_agent_aging(agent_id)
            improvement_reason = self._extract_improvement_reason(aging_analysis)
        
        # 2. Get current metrics
        current_metrics = self._get_agent_metrics(agent)
        
        # 3. Generate improvement suggestions
        suggestions = await self._generate_improvement_suggestions(
            agent=agent,
            current_metrics=current_metrics,
            issues=aging_analysis.get("issues", []) if not improvement_reason else [],
            target_metrics=target_metrics
        )
        
        # 4. Create improved version
        improved_agent = await self._create_improved_version(
            agent=agent,
            suggestions=suggestions,
            improvement_reason=improvement_reason
        )
        
        # 5. Create A/B test experiment
        experiment = await self._create_ab_test(
            original_agent_id=agent_id,
            improved_agent_id=improved_agent.id,
            target_metrics=target_metrics or current_metrics
        )
        
        # 6. Record evolution history
        evolution_entry = EvolutionHistory(
            entity_type=EntityType.AGENT,
            entity_id=agent_id,
            change_type=ChangeType.IMPROVED,
            change_description=f"Agent improvement: {improvement_reason}",
            before_state={
                "agent_id": str(agent_id),
                "version": agent.version,
                "metrics": current_metrics,
                "system_prompt": agent.system_prompt[:200] if agent.system_prompt else None
            },
            after_state={
                "agent_id": str(improved_agent.id),
                "version": improved_agent.version,
                "suggestions": suggestions
            },
            trigger_type=TriggerType.AUTO_OPTIMIZATION,
            trigger_data={
                "improvement_reason": improvement_reason,
                "experiment_id": str(experiment.id) if experiment else None
            }
        )
        self.db.add(evolution_entry)
        self.db.commit()
        
        logger.info(
            f"Created improved version of agent {agent.name}",
            extra={
                "original_agent_id": str(agent_id),
                "improved_agent_id": str(improved_agent.id),
                "experiment_id": str(experiment.id) if experiment else None
            }
        )
        
        return {
            "original_agent_id": str(agent_id),
            "improved_agent_id": str(improved_agent.id),
            "experiment_id": str(experiment.id) if experiment else None,
            "suggestions": suggestions,
            "current_metrics": current_metrics,
            "evolution_entry_id": str(evolution_entry.id)
        }
    
    def _extract_improvement_reason(self, aging_analysis: Dict[str, Any]) -> str:
        """Extract improvement reason from aging analysis"""
        if not aging_analysis.get("is_aging"):
            return "Proactive optimization"
        
        issues = aging_analysis.get("issues", [])
        if not issues:
            return "General improvement"
        
        # Get top issue
        top_issue = issues[0]
        return f"Fix {top_issue.get('type', 'issue')}: {top_issue.get('message', '')}"
    
    def _get_agent_metrics(self, agent: Agent) -> Dict[str, Any]:
        """Get current agent metrics"""
        total_tasks = agent.total_tasks_executed or 0
        success_rate = (agent.successful_tasks / total_tasks * 100) if total_tasks > 0 else 0
        error_rate = (agent.failed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return {
            "total_tasks": total_tasks,
            "successful_tasks": agent.successful_tasks or 0,
            "failed_tasks": agent.failed_tasks or 0,
            "success_rate": success_rate,
            "error_rate": error_rate,
            "avg_execution_time": agent.average_execution_time or 0,
            "health_status": agent.health_status or "unknown"
        }
    
    async def _generate_improvement_suggestions(
        self,
        agent: Agent,
        current_metrics: Dict[str, Any],
        issues: List[Dict[str, Any]],
        target_metrics: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate improvement suggestions using LLM"""
        
        # Build context for LLM
        context = {
            "agent_name": agent.name,
            "agent_description": agent.description,
            "current_metrics": current_metrics,
            "issues": issues[:5],  # Limit to top 5 issues
            "target_metrics": target_metrics,
            "current_system_prompt": agent.system_prompt[:500] if agent.system_prompt else None
        }
        
        prompt = f"""Analyze the following agent and suggest improvements:

Agent: {agent.name}
Description: {agent.description or 'N/A'}

Current Metrics:
- Success Rate: {current_metrics.get('success_rate', 0):.1f}%
- Error Rate: {current_metrics.get('error_rate', 0):.1f}%
- Avg Execution Time: {current_metrics.get('avg_execution_time', 0):.1f}s
- Health Status: {current_metrics.get('health_status', 'unknown')}

Issues Detected:
{chr(10).join([f"- {issue.get('type')}: {issue.get('message')}" for issue in issues]) if issues else "None"}

Target Metrics:
{target_metrics if target_metrics else "Improve current metrics"}

Current System Prompt (first 500 chars):
{context['current_system_prompt'] or 'N/A'}

Suggest specific improvements to:
1. System prompt modifications
2. Capability additions
3. Configuration changes
4. Error handling improvements

Return JSON with suggestions array, each with:
- type: "prompt", "capability", "config", "error_handling"
- description: What to change
- rationale: Why this will help
- expected_improvement: Expected metric improvement
"""
        
        try:
            response = await self.ollama_client.generate(
                prompt=prompt,
                task_type="reasoning",
                model=None,  # Use default reasoning model
                temperature=0.7
            )
            
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                suggestions_data = json.loads(json_match.group())
                return suggestions_data.get("suggestions", [])
            else:
                # Fallback: create basic suggestions from issues
                return self._create_fallback_suggestions(issues, current_metrics)
        except Exception as e:
            logger.warning(f"Failed to generate LLM suggestions: {e}, using fallback")
            return self._create_fallback_suggestions(issues, current_metrics)
    
    def _create_fallback_suggestions(
        self,
        issues: List[Dict[str, Any]],
        current_metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create fallback suggestions based on issues"""
        suggestions = []
        
        for issue in issues:
            issue_type = issue.get("type")
            
            if issue_type == "low_success_rate":
                suggestions.append({
                    "type": "prompt",
                    "description": "Improve system prompt to increase success rate",
                    "rationale": "Low success rate indicates prompt may need refinement",
                    "expected_improvement": "+10-15% success_rate"
                })
            elif issue_type == "high_error_rate":
                suggestions.append({
                    "type": "error_handling",
                    "description": "Add better error handling and validation",
                    "rationale": "High error rate suggests need for better error handling",
                    "expected_improvement": "-10-15% error_rate"
                })
            elif issue_type == "slow_execution":
                suggestions.append({
                    "type": "config",
                    "description": "Optimize configuration for faster execution",
                    "rationale": "Slow execution suggests optimization needed",
                    "expected_improvement": "-20-30% avg_execution_time"
                })
        
        if not suggestions:
            suggestions.append({
                "type": "prompt",
                "description": "General prompt optimization",
                "rationale": "Proactive improvement",
                "expected_improvement": "+5-10% success_rate"
            })
        
        return suggestions
    
    async def _create_improved_version(
        self,
        agent: Agent,
        suggestions: List[Dict[str, Any]],
        improvement_reason: str
    ) -> Agent:
        """Create improved version of agent"""
        
        # Get artifact for this agent
        artifact = self.db.query(Artifact).filter(
            Artifact.type == ArtifactType.AGENT.value,
            Artifact.name == agent.name
        ).first()
        
        # Apply suggestions to create improved prompt
        improved_prompt = await self._apply_suggestions_to_prompt(
            current_prompt=agent.system_prompt or "",
            suggestions=suggestions
        )
        
        # Create new agent version
        improved_agent = Agent(
            name=f"{agent.name}_v{agent.version + 1}",
            description=agent.description,
            system_prompt=improved_prompt,
            capabilities=agent.capabilities,
            model_preference=agent.model_preference,
            temperature=agent.temperature,
            version=agent.version + 1,
            parent_agent_id=agent.id,
            status=AgentStatus.WAITING_APPROVAL.value,  # Needs approval
            created_by="system",
            agent_metadata={
                "improvement_reason": improvement_reason,
                "suggestions_applied": suggestions,
                "parent_version": agent.version
            }
        )
        
        self.db.add(improved_agent)
        self.db.commit()
        self.db.refresh(improved_agent)
        
        # If artifact exists, create new artifact version
        if artifact:
            # Update artifact with improved prompt
            artifact.prompt = improved_prompt
            artifact.version = agent.version + 1
            
            # Create version snapshot
            self.version_service.create_version(
                artifact=artifact,
                changelog=f"Agent improvement: {improvement_reason}",
                metrics=self._get_agent_metrics(agent),
                created_by="system"
            )
        
        return improved_agent
    
    async def _apply_suggestions_to_prompt(
        self,
        current_prompt: str,
        suggestions: List[Dict[str, Any]]
    ) -> str:
        """Apply suggestions to improve system prompt"""
        
        prompt_suggestions = [s for s in suggestions if s.get("type") == "prompt"]
        if not prompt_suggestions:
            return current_prompt
        
        improvement_prompt = f"""Improve the following agent system prompt based on these suggestions:

Current Prompt:
{current_prompt}

Suggestions:
{chr(10).join([f"- {s.get('description')}: {s.get('rationale')}" for s in prompt_suggestions])}

Return the improved prompt that addresses the suggestions while maintaining the core functionality.
Return only the improved prompt, no additional text.
"""
        
        try:
            improved = await self.ollama_client.generate(
                prompt=improvement_prompt,
                task_type="reasoning",
                model=None,
                temperature=0.7
            )
            
            # Clean up response (remove markdown, etc.)
            improved = improved.strip()
            if improved.startswith("```"):
                # Remove code blocks
                improved = re.sub(r'```[a-z]*\n?', '', improved)
                improved = improved.strip()
            
            return improved if improved else current_prompt
        except Exception as e:
            logger.warning(f"Failed to improve prompt: {e}, using original")
            return current_prompt
    
    async def _create_ab_test(
        self,
        original_agent_id: UUID,
        improved_agent_id: UUID,
        target_metrics: Dict[str, Any]
    ) -> Optional[AgentExperiment]:
        """Create A/B test experiment for comparing agents"""
        
        try:
            experiment = self.experiment_service.create_experiment(
                name=f"A/B Test: Agent Improvement",
                description=f"Compare original agent {original_agent_id} with improved version {improved_agent_id}",
                agent_a_id=original_agent_id,
                agent_b_id=improved_agent_id,
                primary_metric="success_rate",
                success_threshold=5.0,  # At least 5% improvement
                min_samples_per_variant=50,
                created_by="system"
            )
            
            return experiment
        except Exception as e:
            logger.warning(f"Failed to create A/B test: {e}")
            return None
    
    async def apply_improvement_if_successful(
        self,
        experiment_id: UUID,
        improved_agent_id: UUID
    ) -> bool:
        """
        Apply improvement if A/B test shows success
        
        Args:
            experiment_id: Experiment ID
            improved_agent_id: Improved agent ID
            
        Returns:
            True if improvement was applied, False otherwise
        """
        experiment = self.db.query(AgentExperiment).filter(
            AgentExperiment.id == experiment_id
        ).first()
        
        if not experiment:
            return False
        
        # Check if experiment is completed and successful
        if experiment.status != ExperimentStatus.COMPLETED.value:
            return False
        
        # Check if improved version is winner
        if experiment.winner == improved_agent_id and experiment.is_significant:
            # Activate improved agent
            improved_agent = self.db.query(Agent).filter(Agent.id == improved_agent_id).first()
            if improved_agent:
                from app.services.agent_service import AgentService
                agent_service = AgentService(self.db)
                
                # Activate improved agent
                improved_agent.status = AgentStatus.ACTIVE.value
                self.db.commit()
                
                # Deprecate original if it exists
                if improved_agent.parent_agent_id:
                    original = self.db.query(Agent).filter(
                        Agent.id == improved_agent.parent_agent_id
                    ).first()
                    if original:
                        original.status = AgentStatus.DEPRECATED.value
                        self.db.commit()
                
                logger.info(
                    f"Applied improvement: activated agent {improved_agent_id}",
                    extra={
                        "experiment_id": str(experiment_id),
                        "improved_agent_id": str(improved_agent_id)
                    }
                )
                
                return True
        
        return False
    
    def process_feedback_for_improvement(
        self,
        agent_id: UUID,
        feedback: Feedback
    ) -> Optional[Dict[str, Any]]:
        """
        Process feedback to generate improvement suggestions
        
        Args:
            agent_id: Agent ID
            feedback: Feedback object
            
        Returns:
            Improvement suggestions or None
        """
        # Mark feedback as processed
        feedback.processed = True
        
        # Extract insights from feedback
        insights = {
            "rating": feedback.rating,
            "comment": feedback.comment,
            "feedback_type": feedback.feedback_type.value if feedback.feedback_type else None
        }
        
        feedback.insights_extracted = insights
        self.db.commit()
        
        # If rating is low (< 3), suggest improvement
        if feedback.rating and feedback.rating < 3:
            logger.info(
                f"Low rating feedback for agent {agent_id}, suggesting improvement",
                extra={"agent_id": str(agent_id), "rating": feedback.rating}
            )
            
            return {
                "should_improve": True,
                "reason": f"Low rating ({feedback.rating}/5): {feedback.comment or 'No comment'}",
                "insights": insights
            }
        
        return None

