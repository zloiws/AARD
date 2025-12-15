from enum import Enum
from sqlalchemy import Column, String, Text, JSON, TIMESTAMP, ForeignKey, Index, Float
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base

class PlanLifecycle(str, Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"

class PlanHypothesis(Base):
    __tablename__ = "plan_hypotheses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    timeline_id = Column(UUID(as_uuid=True), ForeignKey("decision_timelines.id"), nullable=False, index=True)

    # Core plan attributes
    name = Column(String(255), nullable=False)
    description = Column(Text)
    lifecycle = Column(ENUM(PlanLifecycle), nullable=False, default=PlanLifecycle.DRAFT)

    # Hypothesis attributes
    assumptions = Column(JSON)  # List of assumption strings
    risks = Column(JSON)  # List of risk strings with probabilities
    confidence = Column(Float, nullable=False, default=0.5)  # 0.0 to 1.0

    # Plan structure
    steps = Column(JSON)  # Ordered list of plan steps
    dependencies = Column(JSON)  # Graph of step dependencies
    resources = Column(JSON)  # Required resources/capabilities

    # Metadata
    plan_metadata = Column(JSON)  # Additional plan-specific data
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), onupdate=func.now(), nullable=True)

    # Relationships
    timeline = relationship("DecisionTimeline", back_populates="hypotheses")

    __table_args__ = (
        Index('ix_plan_hypotheses_timeline_lifecycle', 'timeline_id', 'lifecycle'),
    )

class PlanHypothesisNode(Base):
    __tablename__ = "plan_hypothesis_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    hypothesis_id = Column(UUID(as_uuid=True), ForeignKey("plan_hypotheses.id"), nullable=False, index=True)
    node_id = Column(UUID(as_uuid=True), ForeignKey("decision_nodes.id"), nullable=False, index=True)

    # Node role in plan
    node_type = Column(String(50), nullable=False)  # 'assumption', 'step', 'risk', 'outcome'
    node_metadata = Column(JSON)

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    hypothesis = relationship("PlanHypothesis", back_populates="nodes")
    node = relationship("DecisionNode", back_populates="plan_nodes")

    __table_args__ = (
        Index('ix_plan_hypothesis_nodes_hypothesis_node', 'hypothesis_id', 'node_id'),
    )

# Add relationships to DecisionTimeline
from backend.app.models.interpretation import DecisionTimeline, DecisionNode

DecisionTimeline.hypotheses = relationship("PlanHypothesis", back_populates="timeline", cascade="all, delete-orphan")
DecisionTimeline.plan_nodes = relationship("PlanHypothesisNode", back_populates="timeline", cascade="all, delete-orphan")

PlanHypothesis.nodes = relationship("PlanHypothesisNode", back_populates="hypothesis", cascade="all, delete-orphan")
DecisionNode.plan_nodes = relationship("PlanHypothesisNode", back_populates="node", cascade="all, delete-orphan")
