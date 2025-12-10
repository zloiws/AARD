"""
SQLAlchemy model for checkpoints
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.core.database import Base


class Checkpoint(Base):
    """
    Checkpoint model for saving entity states
    """
    __tablename__ = "checkpoints"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Entity reference
    entity_type = Column(String(50), nullable=False, index=True)  # plan, task, artifact, etc.
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # State
    state_data = Column(JSONB, nullable=False)
    state_hash = Column(String(64), nullable=True, index=True)  # SHA-256 hash
    
    # Metadata
    reason = Column(String(255), nullable=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    
    # Links
    request_id = Column(UUID(as_uuid=True), ForeignKey("request_logs.id", ondelete="SET NULL"), nullable=True)
    trace_id = Column(String(255), nullable=True, index=True)  # OpenTelemetry trace ID
    
    # Relationships
    request = relationship("RequestLog", foreign_keys=[request_id])
    
    # Indexes
    __table_args__ = (
        Index("idx_checkpoints_entity", "entity_type", "entity_id"),
        Index("idx_checkpoints_created", "created_at"),
    )
    
    def __repr__(self):
        return f"<Checkpoint(id={self.id}, entity={self.entity_type}:{self.entity_id}, reason={self.reason})>"

