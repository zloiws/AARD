"""
Agent Experiment model for A/B testing
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class ExperimentStatus(str, Enum):
    """Experiment status enumeration"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AgentExperiment(Base):
    """Agent A/B testing experiment"""
    __tablename__ = "agent_experiments"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Agent versions being tested
    agent_a_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    agent_b_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)
    
    # Experiment configuration
    status = Column(String(50), nullable=False, default=ExperimentStatus.DRAFT.value)
    traffic_split = Column(Float, nullable=False, default=0.5)  # 0.0-1.0, percentage for agent A
    
    # Metrics to track
    metrics_to_track = Column(JSON, nullable=True)  # List of metric names
    
    # Success criteria
    primary_metric = Column(String(100), nullable=True)  # Main metric to compare
    success_threshold = Column(Float, nullable=True)  # Minimum improvement to consider success
    
    # Experiment duration
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    max_duration_hours = Column(Integer, nullable=True)  # Auto-stop after this duration
    
    # Sample size
    min_samples_per_variant = Column(Integer, nullable=True, default=100)
    max_samples_per_variant = Column(Integer, nullable=True)
    
    # Results
    agent_a_samples = Column(Integer, nullable=False, default=0)
    agent_b_samples = Column(Integer, nullable=False, default=0)
    agent_a_metrics = Column(JSON, nullable=True)  # Aggregated metrics for agent A
    agent_b_metrics = Column(JSON, nullable=True)  # Aggregated metrics for agent B
    
    # Statistical significance
    confidence_level = Column(Float, nullable=True, default=0.95)  # 0.0-1.0
    p_value = Column(Float, nullable=True)  # Statistical p-value
    is_significant = Column(Boolean, nullable=True)  # Whether results are statistically significant
    winner = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=True)  # Winning agent
    
    # Metadata
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True)
    
    # Relationships
    agent_a = relationship("Agent", foreign_keys=[agent_a_id], backref="experiments_as_a")
    agent_b = relationship("Agent", foreign_keys=[agent_b_id], backref="experiments_as_b")
    
    def __repr__(self):
        return f"<AgentExperiment(id={self.id}, name={self.name}, status={self.status})>"


class ExperimentResult(Base):
    """Individual experiment result (one task execution)"""
    __tablename__ = "experiment_results"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    experiment_id = Column(PGUUID(as_uuid=True), ForeignKey("agent_experiments.id"), nullable=False)
    agent_id = Column(PGUUID(as_uuid=True), ForeignKey("agents.id"), nullable=False)  # Which agent was used
    variant = Column(String(1), nullable=False)  # 'A' or 'B'
    
    # Task information
    task_id = Column(PGUUID(as_uuid=True), nullable=True)
    task_description = Column(Text, nullable=True)
    
    # Metrics
    execution_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, nullable=True)
    error_message = Column(Text, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    cost_usd = Column(Float, nullable=True)
    
    # Custom metrics
    custom_metrics = Column(JSON, nullable=True)  # Additional metrics specific to the experiment
    
    # Quality metrics
    quality_score = Column(Float, nullable=True)  # 0.0-1.0, user or system rating
    user_feedback = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    experiment = relationship("AgentExperiment", backref="results")
    agent = relationship("Agent", backref="experiment_results")
    
    def __repr__(self):
        return f"<ExperimentResult(id={self.id}, experiment_id={self.experiment_id}, variant={self.variant}, success={self.success})>"

