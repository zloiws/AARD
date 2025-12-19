"""
Project Metric model for storing project-level metrics
"""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from app.core.database import Base
from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID


class MetricType(str, Enum):
    """Types of project metrics"""
    PERFORMANCE = "performance"  # System performance metrics
    TASK_SUCCESS = "task_success"  # Task execution success rates
    EXECUTION_TIME = "execution_time"  # Execution time metrics
    TASK_DISTRIBUTION = "task_distribution"  # Distribution by task types
    TREND = "trend"  # Trend metrics over time
    AGGREGATE = "aggregate"  # Aggregated metrics


class MetricPeriod(str, Enum):
    """Time periods for metric aggregation"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


class ProjectMetric(Base):
    """
    Model for storing project-level metrics.
    Tracks system performance, task success rates, execution times, and trends.
    """
    __tablename__ = "project_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Metric identification
    metric_type = Column(SQLEnum(MetricType), nullable=False, index=True)
    metric_name = Column(String(255), nullable=False, index=True)  # e.g., "avg_execution_time", "task_success_rate"
    period = Column(SQLEnum(MetricPeriod), nullable=False, index=True)  # Aggregation period
    
    # Time range
    period_start = Column(DateTime, nullable=False, index=True)  # Start of the period
    period_end = Column(DateTime, nullable=False)  # End of the period
    
    # Metric values
    value = Column(Float, nullable=True)  # Primary metric value
    count = Column(Integer, nullable=False, default=0)  # Number of samples
    min_value = Column(Float, nullable=True)  # Minimum value in period
    max_value = Column(Float, nullable=True)  # Maximum value in period
    sum_value = Column(Float, nullable=True)  # Sum of values (for calculating averages)
    
    # Additional data
    metric_metadata = Column(JSONB, nullable=True)  # Additional metric data (breakdowns, distributions, etc.)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_project_metrics_type_name_period', 'metric_type', 'metric_name', 'period'),
        Index('idx_project_metrics_period_start', 'period_start'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary"""
        return {
            "id": str(self.id),
            "metric_type": self.metric_type.value,
            "metric_name": self.metric_name,
            "period": self.period.value,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "value": self.value,
            "count": self.count,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "sum_value": self.sum_value,
            "metadata": self.metric_metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    def __repr__(self):
        return f"<ProjectMetric(id={self.id}, type={self.metric_type.value}, name={self.metric_name}, period={self.period.value}, value={self.value})>"

