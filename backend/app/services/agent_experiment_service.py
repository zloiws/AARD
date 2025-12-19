"""
Agent Experiment Service for A/B testing
"""
import random
import statistics
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.tracing import add_span_attributes, get_tracer
from app.models.agent import Agent
from app.models.agent_experiment import (AgentExperiment, ExperimentResult,
                                         ExperimentStatus)
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class AgentExperimentService:
    """Service for managing agent A/B testing experiments"""
    
    def __init__(self, db: Session):
        self.db = db
        self.tracer = get_tracer(__name__)
    
    def create_experiment(
        self,
        name: str,
        agent_a_id: UUID,
        agent_b_id: UUID,
        description: Optional[str] = None,
        traffic_split: float = 0.5,
        primary_metric: Optional[str] = None,
        success_threshold: Optional[float] = None,
        min_samples_per_variant: int = 100,
        max_samples_per_variant: Optional[int] = None,
        max_duration_hours: Optional[int] = None,
        metrics_to_track: Optional[List[str]] = None,
        confidence_level: float = 0.95,
        created_by: Optional[str] = None
    ) -> AgentExperiment:
        """
        Create a new A/B testing experiment
        
        Args:
            name: Experiment name
            agent_a_id: ID of agent A (control)
            agent_b_id: ID of agent B (variant)
            description: Experiment description
            traffic_split: Percentage of traffic for agent A (0.0-1.0)
            primary_metric: Main metric to compare (e.g., 'success_rate', 'quality_score')
            success_threshold: Minimum improvement to consider success
            min_samples_per_variant: Minimum samples before considering results
            max_samples_per_variant: Maximum samples per variant
            max_duration_hours: Auto-stop after this duration
            metrics_to_track: List of metric names to track
            confidence_level: Statistical confidence level (0.0-1.0)
            created_by: User who created the experiment
            
        Returns:
            Created experiment
        """
        # Validate agents exist
        agent_a = self.db.query(Agent).filter(Agent.id == agent_a_id).first()
        agent_b = self.db.query(Agent).filter(Agent.id == agent_b_id).first()
        
        if not agent_a:
            raise ValueError(f"Agent A {agent_a_id} not found")
        if not agent_b:
            raise ValueError(f"Agent B {agent_b_id} not found")
        
        if agent_a_id == agent_b_id:
            raise ValueError("Agent A and Agent B must be different")
        
        # Validate traffic split
        if not 0.0 <= traffic_split <= 1.0:
            raise ValueError("traffic_split must be between 0.0 and 1.0")
        
        experiment = AgentExperiment(
            name=name,
            description=description,
            agent_a_id=agent_a_id,
            agent_b_id=agent_b_id,
            status=ExperimentStatus.DRAFT.value,
            traffic_split=traffic_split,
            primary_metric=primary_metric or "success_rate",
            success_threshold=success_threshold,
            min_samples_per_variant=min_samples_per_variant,
            max_samples_per_variant=max_samples_per_variant,
            max_duration_hours=max_duration_hours,
            metrics_to_track=metrics_to_track or ["success_rate", "execution_time_ms", "quality_score"],
            confidence_level=confidence_level,
            created_by=created_by
        )
        
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        
        logger.info(
            f"Created experiment: {name}",
            extra={
                "experiment_id": str(experiment.id),
                "agent_a_id": str(agent_a_id),
                "agent_b_id": str(agent_b_id),
            }
        )
        
        return experiment
    
    def start_experiment(self, experiment_id: UUID) -> AgentExperiment:
        """Start an experiment"""
        experiment = self.db.query(AgentExperiment).filter(
            AgentExperiment.id == experiment_id
        ).first()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status != ExperimentStatus.DRAFT.value:
            raise ValueError(f"Experiment must be in DRAFT status to start, current: {experiment.status}")
        
        experiment.status = ExperimentStatus.RUNNING.value
        experiment.start_date = datetime.now(timezone.utc)
        
        if experiment.max_duration_hours:
            experiment.end_date = experiment.start_date + timedelta(hours=experiment.max_duration_hours)
        
        self.db.commit()
        self.db.refresh(experiment)
        
        logger.info(f"Started experiment: {experiment.name}", extra={"experiment_id": str(experiment_id)})
        
        return experiment
    
    def select_variant(self, experiment_id: UUID) -> tuple[UUID, str]:
        """
        Select which agent variant to use for a task
        
        Returns:
            Tuple of (agent_id, variant) where variant is 'A' or 'B'
        """
        experiment = self.db.query(AgentExperiment).filter(
            and_(
                AgentExperiment.id == experiment_id,
                AgentExperiment.status == ExperimentStatus.RUNNING.value
            )
        ).first()
        
        if not experiment:
            raise ValueError(f"Running experiment {experiment_id} not found")
        
        # Check if we've reached max samples
        if experiment.max_samples_per_variant:
            if experiment.agent_a_samples >= experiment.max_samples_per_variant:
                return (experiment.agent_b_id, 'B')
            if experiment.agent_b_samples >= experiment.max_samples_per_variant:
                return (experiment.agent_a_id, 'A')
        
        # Use traffic split to select variant
        if random.random() < experiment.traffic_split:
            return (experiment.agent_a_id, 'A')
        else:
            return (experiment.agent_b_id, 'B')
    
    def record_result(
        self,
        experiment_id: UUID,
        agent_id: UUID,
        variant: str,
        success: Optional[bool] = None,
        execution_time_ms: Optional[int] = None,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        quality_score: Optional[float] = None,
        error_message: Optional[str] = None,
        task_id: Optional[UUID] = None,
        task_description: Optional[str] = None,
        custom_metrics: Optional[Dict[str, Any]] = None,
        user_feedback: Optional[str] = None
    ) -> ExperimentResult:
        """
        Record a result for an experiment
        
        Args:
            experiment_id: Experiment ID
            agent_id: Agent that was used
            variant: 'A' or 'B'
            success: Whether the task succeeded
            execution_time_ms: Execution time in milliseconds
            tokens_used: Number of tokens used
            cost_usd: Cost in USD
            quality_score: Quality score (0.0-1.0)
            error_message: Error message if failed
            task_id: Task ID
            task_description: Task description
            custom_metrics: Additional custom metrics
            user_feedback: User feedback
            
        Returns:
            Created result
        """
        experiment = self.db.query(AgentExperiment).filter(
            AgentExperiment.id == experiment_id
        ).first()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if variant not in ['A', 'B']:
            raise ValueError("variant must be 'A' or 'B'")
        
        result = ExperimentResult(
            experiment_id=experiment_id,
            agent_id=agent_id,
            variant=variant,
            task_id=task_id,
            task_description=task_description,
            success=success,
            execution_time_ms=execution_time_ms,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
            quality_score=quality_score,
            error_message=error_message,
            custom_metrics=custom_metrics,
            user_feedback=user_feedback
        )
        
        self.db.add(result)
        
        # Update experiment sample counts
        if variant == 'A':
            experiment.agent_a_samples += 1
        else:
            experiment.agent_b_samples += 1
        
        self.db.commit()
        self.db.refresh(result)
        
        # Check if we should auto-complete
        if experiment.status == ExperimentStatus.RUNNING.value:
            self._check_auto_complete(experiment)
        
        return result
    
    def _check_auto_complete(self, experiment: AgentExperiment):
        """Check if experiment should be auto-completed"""
        # Check duration
        if experiment.end_date and datetime.now(timezone.utc) >= experiment.end_date:
            self.complete_experiment(experiment.id)
            return
        
        # Check sample size
        if experiment.min_samples_per_variant:
            if (experiment.agent_a_samples >= experiment.min_samples_per_variant and
                experiment.agent_b_samples >= experiment.min_samples_per_variant):
                # Calculate statistics and check if significant
                self._calculate_statistics(experiment)
                
                # If significant, we could auto-complete, but for now we'll let user decide
                pass
    
    def _calculate_statistics(self, experiment: AgentExperiment):
        """Calculate statistical significance of results"""
        # Get results for both variants
        results_a = self.db.query(ExperimentResult).filter(
            and_(
                ExperimentResult.experiment_id == experiment.id,
                ExperimentResult.variant == 'A'
            )
        ).all()
        
        results_b = self.db.query(ExperimentResult).filter(
            and_(
                ExperimentResult.experiment_id == experiment.id,
                ExperimentResult.variant == 'B'
            )
        ).all()
        
        if not results_a or not results_b:
            return
        
        # Calculate metrics based on primary_metric
        if experiment.primary_metric == "success_rate":
            metric_a = sum(1 for r in results_a if r.success) / len(results_a) if results_a else 0.0
            metric_b = sum(1 for r in results_b if r.success) / len(results_b) if results_b else 0.0
        elif experiment.primary_metric == "quality_score":
            scores_a = [r.quality_score for r in results_a if r.quality_score is not None]
            scores_b = [r.quality_score for r in results_b if r.quality_score is not None]
            metric_a = statistics.mean(scores_a) if scores_a else 0.0
            metric_b = statistics.mean(scores_b) if scores_b else 0.0
        elif experiment.primary_metric == "execution_time_ms":
            times_a = [r.execution_time_ms for r in results_a if r.execution_time_ms is not None]
            times_b = [r.execution_time_ms for r in results_b if r.execution_time_ms is not None]
            metric_a = statistics.mean(times_a) if times_a else 0.0
            metric_b = statistics.mean(times_b) if times_b else 0.0
        else:
            # Default to success rate
            metric_a = sum(1 for r in results_a if r.success) / len(results_a) if results_a else 0.0
            metric_b = sum(1 for r in results_b if r.success) / len(results_b) if results_b else 0.0
        
        # Simple t-test approximation (for binary metrics)
        # For more accurate results, use scipy.stats
        n_a = len(results_a)
        n_b = len(results_b)
        
        # Calculate p-value using two-proportion z-test approximation
        p_a = metric_a
        p_b = metric_b
        p_pooled = (n_a * p_a + n_b * p_b) / (n_a + n_b) if (n_a + n_b) > 0 else 0.0
        
        if p_pooled > 0 and p_pooled < 1:
            se = (p_pooled * (1 - p_pooled) * (1/n_a + 1/n_b)) ** 0.5
            if se > 0:
                z = (p_b - p_a) / se
                # Approximate p-value (two-tailed)
                # For simplicity, using normal approximation
                p_value = 2 * (1 - abs(z) / 3.0)  # Simplified approximation
                p_value = max(0.0, min(1.0, p_value))
            else:
                p_value = 1.0
        else:
            p_value = 1.0
        
        # Determine significance
        alpha = 1 - experiment.confidence_level
        is_significant = p_value < alpha
        
        # Determine winner
        winner = None
        if is_significant:
            if experiment.primary_metric in ["execution_time_ms"]:
                # Lower is better
                winner = experiment.agent_a_id if metric_a < metric_b else experiment.agent_b_id
            else:
                # Higher is better
                winner = experiment.agent_a_id if metric_a > metric_b else experiment.agent_b_id
        
        # Update experiment
        experiment.agent_a_metrics = {
            experiment.primary_metric: metric_a,
            "samples": n_a
        }
        experiment.agent_b_metrics = {
            experiment.primary_metric: metric_b,
            "samples": n_b
        }
        experiment.p_value = p_value
        experiment.is_significant = is_significant
        experiment.winner = winner
        
        self.db.commit()
        self.db.refresh(experiment)
    
    def complete_experiment(self, experiment_id: UUID) -> AgentExperiment:
        """Complete an experiment and calculate final statistics"""
        experiment = self.db.query(AgentExperiment).filter(
            AgentExperiment.id == experiment_id
        ).first()
        
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")
        
        if experiment.status not in [ExperimentStatus.RUNNING.value, ExperimentStatus.PAUSED.value]:
            raise ValueError(f"Cannot complete experiment in status: {experiment.status}")
        
        # Calculate final statistics
        self._calculate_statistics(experiment)
        
        experiment.status = ExperimentStatus.COMPLETED.value
        experiment.end_date = datetime.now(timezone.utc)
        
        self.db.commit()
        self.db.refresh(experiment)
        
        logger.info(
            f"Completed experiment: {experiment.name}",
            extra={
                "experiment_id": str(experiment_id),
                "winner": str(experiment.winner) if experiment.winner else None,
                "is_significant": experiment.is_significant
            }
        )
        
        return experiment
    
    def get_experiment(self, experiment_id: UUID) -> Optional[AgentExperiment]:
        """Get experiment by ID"""
        return self.db.query(AgentExperiment).filter(
            AgentExperiment.id == experiment_id
        ).first()
    
    def list_experiments(
        self,
        status: Optional[ExperimentStatus] = None,
        agent_id: Optional[UUID] = None,
        limit: Optional[int] = None
    ) -> List[AgentExperiment]:
        """List experiments with optional filters"""
        query = self.db.query(AgentExperiment)
        
        if status:
            query = query.filter(AgentExperiment.status == status.value)
        
        if agent_id:
            query = query.filter(
                or_(
                    AgentExperiment.agent_a_id == agent_id,
                    AgentExperiment.agent_b_id == agent_id
                )
            )
        
        if limit:
            query = query.limit(limit)
        
        return query.order_by(AgentExperiment.created_at.desc()).all()
    
    def get_experiment_results(
        self,
        experiment_id: UUID,
        variant: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[ExperimentResult]:
        """Get results for an experiment"""
        query = self.db.query(ExperimentResult).filter(
            ExperimentResult.experiment_id == experiment_id
        )
        
        if variant:
            query = query.filter(ExperimentResult.variant == variant)
        
        if limit:
            query = query.limit(limit)
        
        return query.order_by(ExperimentResult.created_at.desc()).all()

