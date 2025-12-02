"""
Artifact model (agents and tools)
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import uuid4, UUID

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum, Float, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ARRAY
from sqlalchemy.orm import relationship

from app.core.database import Base


class ArtifactType(str, Enum):
    """Artifact type enumeration"""
    AGENT = "agent"
    TOOL = "tool"


class ArtifactStatus(str, Enum):
    """Artifact status enumeration"""
    DRAFT = "draft"
    WAITING_APPROVAL = "waiting_approval"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class Artifact(Base):
    """Artifact model (agents and tools)"""
    __tablename__ = "artifacts"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    type = Column(String(50), nullable=False)  # Use String to match DB constraint (lowercase)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    code = Column(Text, nullable=True)  # For tools
    prompt = Column(Text, nullable=True)  # For agents
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(50), nullable=False, default="draft")  # Use String to match DB constraint (lowercase)
    test_results = Column(JSON, nullable=True)  # Test results as JSON
    security_rating = Column(Float, nullable=True)  # Security rating 0.0-1.0
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=True)
    
    def __repr__(self):
        return f"<Artifact(id={self.id}, type={self.type}, name={self.name}, version={self.version})>"


class ArtifactDependency(Base):
    """Artifact dependencies"""
    __tablename__ = "artifact_dependencies"
    
    artifact_id = Column(PGUUID(as_uuid=True), ForeignKey("artifacts.id"), primary_key=True)
    depends_on_artifact_id = Column(PGUUID(as_uuid=True), ForeignKey("artifacts.id"), primary_key=True)
    
    # Relationships
    artifact = relationship("Artifact", foreign_keys=[artifact_id], backref="dependencies")
    depends_on = relationship("Artifact", foreign_keys=[depends_on_artifact_id], backref="dependent_artifacts")

