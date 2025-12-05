"""
Audit Report model for storing self-audit results
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, DateTime, Text, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class AuditType(str, Enum):
    """Type of audit"""
    PERFORMANCE = "performance"
    QUALITY = "quality"
    PROMPTS = "prompts"
    ERRORS = "errors"
    FULL = "full"  # Complete audit


class AuditStatus(str, Enum):
    """Status of audit"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AuditReport(Base):
    """
    Model for storing self-audit reports
    """
    __tablename__ = "audit_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_type = Column(SQLEnum(AuditType), nullable=False, index=True)
    status = Column(SQLEnum(AuditStatus), nullable=False, default=AuditStatus.PENDING, index=True)
    
    # Period covered by audit
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False, index=True)
    
    # Audit results
    summary = Column(Text, nullable=True)  # Human-readable summary
    findings = Column(JSONB, nullable=True)  # Detailed findings
    recommendations = Column(JSONB, nullable=True)  # Recommendations for improvement
    metrics = Column(JSONB, nullable=True)  # Metrics analyzed
    trends = Column(JSONB, nullable=True)  # Trend analysis
    
    # Metadata
    audit_metadata = Column(JSONB, nullable=True)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit report to dictionary"""
        return {
            "id": str(self.id),
            "audit_type": self.audit_type.value if isinstance(self.audit_type, Enum) else self.audit_type,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "metrics": self.metrics,
            "trends": self.trends,
            "audit_metadata": self.audit_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def __repr__(self):
        return f"<AuditReport(id={self.id}, type={self.audit_type}, status={self.status})>"

