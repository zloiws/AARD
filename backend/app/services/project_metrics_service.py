"""
Project Metrics Service for tracking project-level metrics
Provides metrics collection, aggregation, and analysis at the project level
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.project_metric import ProjectMetric, MetricType, MetricPeriod
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.trace import ExecutionTrace

logger = LoggingConfig.get_logger(__name__)


class ProjectMetricsService:
    """
    Service for tracking project-level metrics:
    - Overall system performance
    - Task execution success rates
    - Average execution times
    - Distribution by task types
    - Trends over time
    """
    
    def __init__(self, db: Session = None):
        """
        Initialize Project Metrics Service
        
        Args:
            db: Database session (optional)
        """
        self.db = db or SessionLocal()
    
    def record_metric(
        self,
        metric_type: MetricType,
        metric_name: str,
        value: float,
        period: MetricPeriod,
        period_start: datetime,
        period_end: datetime,
        count: int = 1,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        sum_value: Optional[float] = None,
        metric_metadata: Optional[Dict[str, Any]] = None
    ) -> ProjectMetric:
        """
        Record a project metric
        
        Args:
            metric_type: Type of metric
            metric_name: Name of the metric
            value: Primary metric value
            period: Aggregation period
            period_start: Start of the period
            period_end: End of the period
            count: Number of samples
            min_value: Minimum value
            max_value: Maximum value
            sum_value: Sum of values
            metric_metadata: Additional metadata
            
        Returns:
            Created ProjectMetric instance
        """
        try:
            # Check if metric already exists for this period
            existing = self.db.query(ProjectMetric).filter(
                and_(
                    ProjectMetric.metric_type == metric_type,
                    ProjectMetric.metric_name == metric_name,
                    ProjectMetric.period == period,
                    ProjectMetric.period_start == period_start
                )
            ).first()
            
            if existing:
                # Update existing metric
                existing.value = value
                existing.count = count
                if min_value is not None:
                    existing.min_value = min_value
                if max_value is not None:
                    existing.max_value = max_value
                if sum_value is not None:
                    existing.sum_value = sum_value
                if metric_metadata is not None:
                    existing.metric_metadata = metric_metadata
                existing.updated_at = datetime.now(timezone.utc)
                self.db.commit()
                self.db.refresh(existing)
                return existing
            else:
                # Create new metric
                metric = ProjectMetric(
                    metric_type=metric_type,
                    metric_name=metric_name,
                    period=period,
                    period_start=period_start,
                    period_end=period_end,
                    value=value,
                    count=count,
                    min_value=min_value or value,
                    max_value=max_value or value,
                    sum_value=sum_value or value,
                    metric_metadata=metric_metadata
                )
                self.db.add(metric)
                self.db.commit()
                self.db.refresh(metric)
                return metric
                
        except Exception as e:
            logger.error(f"Error recording metric: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def collect_performance_metrics(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """
        Collect overall system performance metrics for a time period
        
        Args:
            period_start: Start of the period
            period_end: End of the period
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            # Get tasks in period
            tasks = self.db.query(Task).filter(
                and_(
                    Task.created_at >= period_start,
                    Task.created_at < period_end
                )
            ).all()
            
            total_tasks = len(tasks)
            completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
            failed = sum(1 for t in tasks if t.status == TaskStatus.FAILED)
            success_rate = completed / total_tasks if total_tasks > 0 else 0.0
            
            # Get execution traces for timing
            traces = self.db.query(ExecutionTrace).filter(
                and_(
                    ExecutionTrace.created_at >= period_start,
                    ExecutionTrace.created_at < period_end
                )
            ).all()
            
            execution_times = []
            for trace in traces:
                if trace.duration_ms:
                    execution_times.append(trace.duration_ms / 1000.0)  # Convert to seconds
            
            avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else None
            min_execution_time = min(execution_times) if execution_times else None
            max_execution_time = max(execution_times) if execution_times else None
            
            metrics = {
                "total_tasks": total_tasks,
                "completed_tasks": completed,
                "failed_tasks": failed,
                "success_rate": success_rate,
                "avg_execution_time": avg_execution_time,
                "min_execution_time": min_execution_time,
                "max_execution_time": max_execution_time,
                "total_executions": len(traces)
            }
            
            # Determine period type
            period_duration = period_end - period_start
            if period_duration <= timedelta(hours=1):
                period = MetricPeriod.HOUR
            elif period_duration <= timedelta(days=1):
                period = MetricPeriod.DAY
            elif period_duration <= timedelta(weeks=1):
                period = MetricPeriod.WEEK
            else:
                period = MetricPeriod.MONTH
            
            # Record metrics
            if total_tasks > 0:
                self.record_metric(
                    metric_type=MetricType.PERFORMANCE,
                    metric_name="task_success_rate",
                    value=success_rate,
                    period=period,
                    period_start=period_start,
                    period_end=period_end,
                    count=total_tasks,
                    metric_metadata={"completed": completed, "failed": failed}
                )
            
            if avg_execution_time is not None:
                self.record_metric(
                    metric_type=MetricType.EXECUTION_TIME,
                    metric_name="avg_execution_time",
                    value=avg_execution_time,
                    period=period,
                    period_start=period_start,
                    period_end=period_end,
                    count=len(execution_times),
                    min_value=min_execution_time,
                    max_value=max_execution_time,
                    sum_value=sum(execution_times),
                    metric_metadata=None
                )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {e}", exc_info=True)
            return {}
    
    def collect_task_distribution(self, period_start: datetime, period_end: datetime) -> Dict[str, Any]:
        """
        Collect task distribution metrics by status and type
        
        Args:
            period_start: Start of the period
            period_end: End of the period
            
        Returns:
            Dictionary with distribution metrics
        """
        try:
            tasks = self.db.query(Task).filter(
                and_(
                    Task.created_at >= period_start,
                    Task.created_at < period_end
                )
            ).all()
            
            # Distribution by status
            status_distribution = {}
            for status in TaskStatus:
                status_distribution[status.value] = sum(1 for t in tasks if t.status == status)
            
            # Distribution by priority
            priority_distribution = {}
            for priority in range(10):
                priority_distribution[priority] = sum(1 for t in tasks if t.priority == priority)
            
            # Distribution by autonomy level
            autonomy_distribution = {}
            for level in range(5):
                autonomy_distribution[level] = sum(1 for t in tasks if t.autonomy_level == level)
            
            metrics = {
                "status_distribution": status_distribution,
                "priority_distribution": priority_distribution,
                "autonomy_distribution": autonomy_distribution,
                "total_tasks": len(tasks)
            }
            
            # Determine period type
            period_duration = period_end - period_start
            if period_duration <= timedelta(hours=1):
                period = MetricPeriod.HOUR
            elif period_duration <= timedelta(days=1):
                period = MetricPeriod.DAY
            elif period_duration <= timedelta(weeks=1):
                period = MetricPeriod.WEEK
            else:
                period = MetricPeriod.MONTH
            
            # Record metric
            self.record_metric(
                metric_type=MetricType.TASK_DISTRIBUTION,
                metric_name="task_distribution",
                value=len(tasks),
                period=period,
                period_start=period_start,
                period_end=period_end,
                count=len(tasks),
                metric_metadata=metrics
            )
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting task distribution: {e}", exc_info=True)
            return {}
    
    def get_overview(self, days: int = 30) -> Dict[str, Any]:
        """
        Get overview of project metrics
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with overview metrics
        """
        try:
            period_end = datetime.now(timezone.utc)
            period_start = period_end - timedelta(days=days)
            
            # Collect current metrics
            performance = self.collect_performance_metrics(period_start, period_end)
            distribution = self.collect_task_distribution(period_start, period_end)
            
            # Get plans statistics
            plans = self.db.query(Plan).filter(
                and_(
                    Plan.created_at >= period_start,
                    Plan.created_at < period_end
                )
            ).all()
            
            total_plans = len(plans)
            completed_plans = sum(1 for p in plans if p.status == PlanStatus.COMPLETED.value)
            failed_plans = sum(1 for p in plans if p.status == PlanStatus.FAILED.value)
            
            # Get recent metrics from database
            recent_metrics = self.db.query(ProjectMetric).filter(
                and_(
                    ProjectMetric.period_start >= period_start,
                    ProjectMetric.period_start < period_end
                )
            ).order_by(desc(ProjectMetric.period_start)).limit(100).all()
            
            return {
                "period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat(),
                    "days": days
                },
                "performance": performance,
                "distribution": distribution,
                "plans": {
                    "total": total_plans,
                    "completed": completed_plans,
                    "failed": failed_plans,
                    "success_rate": completed_plans / total_plans if total_plans > 0 else 0.0
                },
                "recent_metrics": [m.to_dict() for m in recent_metrics[:10]]  # Last 10 metrics
            }
            
        except Exception as e:
            logger.error(f"Error getting overview: {e}", exc_info=True)
            return {}
    
    def get_trends(
        self,
        metric_name: str,
        metric_type: Optional[MetricType] = None,
        days: int = 30,
        period: MetricPeriod = MetricPeriod.DAY
    ) -> List[Dict[str, Any]]:
        """
        Get trends for a specific metric
        
        Args:
            metric_name: Name of the metric
            metric_type: Optional metric type filter
            days: Number of days to analyze
            period: Aggregation period
            
        Returns:
            List of metric values over time
        """
        try:
            period_end = datetime.now(timezone.utc)
            period_start = period_end - timedelta(days=days)
            
            query = self.db.query(ProjectMetric).filter(
                and_(
                    ProjectMetric.metric_name == metric_name,
                    ProjectMetric.period == period,
                    ProjectMetric.period_start >= period_start,
                    ProjectMetric.period_start < period_end
                )
            )
            
            if metric_type:
                query = query.filter(ProjectMetric.metric_type == metric_type)
            
            metrics = query.order_by(ProjectMetric.period_start).all()
            
            return [m.to_dict() for m in metrics]
            
        except Exception as e:
            logger.error(f"Error getting trends: {e}", exc_info=True)
            return []
    
    def compare_periods(
        self,
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime
    ) -> Dict[str, Any]:
        """
        Compare metrics between two periods
        
        Args:
            period1_start: Start of first period
            period1_end: End of first period
            period2_start: Start of second period
            period2_end: End of second period
            
        Returns:
            Dictionary with comparison results
        """
        try:
            # Collect metrics for both periods
            metrics1 = self.collect_performance_metrics(period1_start, period1_end)
            metrics2 = self.collect_performance_metrics(period2_start, period2_end)
            
            comparison = {
                "period1": {
                    "start": period1_start.isoformat(),
                    "end": period1_end.isoformat(),
                    "metrics": metrics1
                },
                "period2": {
                    "start": period2_start.isoformat(),
                    "end": period2_end.isoformat(),
                    "metrics": metrics2
                },
                "changes": {}
            }
            
            # Calculate changes
            if metrics1.get("success_rate") and metrics2.get("success_rate"):
                comparison["changes"]["success_rate"] = {
                    "absolute": metrics2["success_rate"] - metrics1["success_rate"],
                    "relative": ((metrics2["success_rate"] - metrics1["success_rate"]) / metrics1["success_rate"] * 100) if metrics1["success_rate"] > 0 else 0.0
                }
            
            if metrics1.get("avg_execution_time") and metrics2.get("avg_execution_time"):
                comparison["changes"]["avg_execution_time"] = {
                    "absolute": metrics2["avg_execution_time"] - metrics1["avg_execution_time"],
                    "relative": ((metrics2["avg_execution_time"] - metrics1["avg_execution_time"]) / metrics1["avg_execution_time"] * 100) if metrics1["avg_execution_time"] > 0 else 0.0
                }
            
            if metrics1.get("total_tasks") and metrics2.get("total_tasks"):
                comparison["changes"]["total_tasks"] = {
                    "absolute": metrics2["total_tasks"] - metrics1["total_tasks"],
                    "relative": ((metrics2["total_tasks"] - metrics1["total_tasks"]) / metrics1["total_tasks"] * 100) if metrics1["total_tasks"] > 0 else 0.0
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing periods: {e}", exc_info=True)
            return {}

