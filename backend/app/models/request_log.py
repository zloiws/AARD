"""
SQLAlchemy models for request logging and ranking
"""
import uuid
from datetime import datetime, timezone

from app.core.database import Base
from sqlalchemy import (CheckConstraint, Column, DateTime, Float, ForeignKey,
                        Index, Integer, String, Text)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import relationship


class RequestLog(Base):
    """
    Request log model for storing all requests with ranking
    """
    __tablename__ = "request_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Request information
    request_type = Column(String(50), nullable=False, index=True)  # chat, plan_generation, artifact_generation, etc.
    request_data = Column(JSONB, nullable=False)
    model_used = Column(String(255), nullable=True, index=True)
    server_url = Column(String(255), nullable=True)
    
    # Result
    status = Column(
        String(20),
        CheckConstraint("status IN ('success', 'failed', 'timeout', 'cancelled')"),
        nullable=False,
        index=True
    )
    response_data = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    # Consequences
    created_artifacts = Column(ARRAY(UUID), nullable=True)
    created_plans = Column(ARRAY(UUID), nullable=True)
    created_approvals = Column(ARRAY(UUID), nullable=True)
    modified_artifacts = Column(ARRAY(UUID), nullable=True)
    
    # Ranking scores
    success_score = Column(Float, default=0.5, nullable=False)
    importance_score = Column(Float, default=0.5, nullable=False)
    impact_score = Column(Float, default=0.5, nullable=False)
    overall_rank = Column(Float, default=0.5, nullable=False, index=True)
    
    # Metadata
    user_id = Column(String(255), nullable=True)
    session_id = Column(String(255), nullable=True, index=True)
    trace_id = Column(String(255), nullable=True, index=True)  # Link to OpenTelemetry trace
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    consequences = relationship("RequestConsequence", back_populates="request", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index("idx_request_logs_status", "status"),
        Index("idx_request_logs_type", "request_type"),
        Index("idx_request_logs_rank", "overall_rank"),
        Index("idx_request_logs_created_at", "created_at"),
        Index("idx_request_logs_model", "model_used"),
        Index("idx_request_logs_trace_id", "trace_id"),
    )
    
    def __repr__(self):
        return f"<RequestLog(id={self.id}, type={self.request_type}, status={self.status}, rank={self.overall_rank})>"


class RequestConsequence(Base):
    """
    Request consequence model for tracking what was created/modified by a request
    """
    __tablename__ = "request_consequences"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("request_logs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Consequence type
    consequence_type = Column(String(50), nullable=False)  # artifact_created, plan_created, approval_created, etc.
    entity_type = Column(String(50), nullable=False, index=True)  # artifact, plan, approval, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Impact
    impact_type = Column(String(50), nullable=True)  # positive, negative, neutral
    impact_description = Column(Text, nullable=True)
    impact_score = Column(Float, default=0.0, nullable=False)  # -1.0 to 1.0
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    request = relationship("RequestLog", back_populates="consequences")
    
    # Indexes
    __table_args__ = (
        Index("idx_consequences_request", "request_id"),
        Index("idx_consequences_entity", "entity_type", "entity_id"),
    )
    
    def __repr__(self):
        return f"<RequestConsequence(id={self.id}, type={self.consequence_type}, entity={self.entity_type}:{self.entity_id})>"

