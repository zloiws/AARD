"""
Artifact Version model for version control
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Float, JSON, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class ArtifactVersion(Base):
    """
    Artifact Version model for tracking versions of artifacts (agents and tools)
    
    Stores:
    - Full snapshot of artifact at each version
    - Changelog describing changes
    - Metrics for comparison
    - Automatic rollback capability
    """
    __tablename__ = "artifact_versions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    artifact_id = Column(PGUUID(as_uuid=True), ForeignKey("artifacts.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    
    # Snapshot of artifact data at this version
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=True)  # For tools
    prompt = Column(Text, nullable=True)  # For agents
    type = Column(String(50), nullable=False)  # agent or tool
    
    # Version metadata
    changelog = Column(Text, nullable=True)  # Description of changes in this version
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    created_by = Column(String(255), nullable=True)
    
    # Metrics for comparison and rollback decisions
    metrics = Column(JSONB, nullable=True)  # Performance metrics: success_rate, avg_execution_time, etc.
    test_results = Column(JSON, nullable=True)  # Test results snapshot
    security_rating = Column(Float, nullable=True)  # Security rating 0.0-1.0
    
    # Status tracking
    is_active = Column(String(50), nullable=False, default="false")  # "true" if this is the active version
    promoted_at = Column(DateTime, nullable=True)  # When this version was promoted to active
    deprecated_at = Column(DateTime, nullable=True)  # When this version was deprecated
    
    # Rollback information
    rolled_back_from_version = Column(Integer, nullable=True)  # If this version was created by rollback
    rollback_reason = Column(Text, nullable=True)  # Reason for rollback
    
    # Relationships
    artifact = relationship("Artifact", backref="versions")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_artifact_version', 'artifact_id', 'version', unique=True),
        Index('idx_artifact_active', 'artifact_id', 'is_active'),
    )
    
    def __repr__(self):
        return f"<ArtifactVersion(id={self.id}, artifact_id={self.artifact_id}, version={self.version}, is_active={self.is_active})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert version to dictionary"""
        return {
            "id": str(self.id),
            "artifact_id": str(self.artifact_id),
            "version": self.version,
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "changelog": self.changelog,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": self.created_by,
            "metrics": self.metrics,
            "test_results": self.test_results,
            "security_rating": self.security_rating,
            "is_active": self.is_active == "true",
            "promoted_at": self.promoted_at.isoformat() if self.promoted_at else None,
            "deprecated_at": self.deprecated_at.isoformat() if self.deprecated_at else None,
            "rolled_back_from_version": self.rolled_back_from_version,
            "rollback_reason": self.rollback_reason
        }

