"""
Models for Interpretation rules and Decision Timeline / nodes for observability.
"""
from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, String, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class InterpretationRule(Base):
    """Derived interpretation rule produced by MetaLearningService."""
    __tablename__ = "interpretation_rules"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    source = Column(String(128), nullable=True)  # reflection/meta_learning/manual
    confidence = Column(Float, nullable=True, default=0.0)
    content = Column(JSONB, nullable=True)
    lifecycle = Column(String(32), nullable=False, default="active")  # active/decaying/deprecated
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class DecisionTimeline(Base):
    """A timeline/session for a single user request / workflow run."""
    __tablename__ = "decision_timelines"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(String(128), nullable=False, unique=True, index=True)
    timeline_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    nodes = relationship("DecisionNode", back_populates="timeline", cascade="all, delete-orphan")
    edges = relationship("DecisionEdge", back_populates="timeline", cascade="all, delete-orphan")


class DecisionNode(Base):
    """Node in the decision/timeline graph (Intent/Interpretation/Plan/Execution/Reflection)."""
    __tablename__ = "decision_nodes"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    timeline_id = Column(PGUUID(as_uuid=True), ForeignKey("decision_timelines.id"), nullable=False, index=True)
    node_type = Column(String(64), nullable=False)  # e.g., intent, interpretation, plan, execution_step, reflection
    payload = Column(JSONB, nullable=True)
    status = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    timeline = relationship("DecisionTimeline", back_populates="nodes")


class DecisionEdge(Base):
    """Named edge between two nodes in the decision graph."""
    __tablename__ = "decision_edges"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    timeline_id = Column(PGUUID(as_uuid=True), ForeignKey("decision_timelines.id"), nullable=False, index=True)
    from_node = Column(PGUUID(as_uuid=True), nullable=False)
    to_node = Column(PGUUID(as_uuid=True), nullable=False)
    relation = Column(String(64), nullable=False)  # e.g., interpreted_as, planned_because
    edge_metadata = Column('metadata', JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    timeline = relationship("DecisionTimeline", back_populates="edges")


