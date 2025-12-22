"""
Approval request model
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from app.core.database import Base
from sqlalchemy import JSON, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship


class ApprovalRequestType(str, Enum):
    """Approval request type enumeration"""
    NEW_ARTIFACT = "new_artifact"
    ARTIFACT_UPDATE = "artifact_update"
    PROMPT_CHANGE = "prompt_change"
    EXECUTION_STEP = "execution_step"
    PLAN_APPROVAL = "plan_approval"


class ApprovalRequestStatus(str, Enum):
    """Approval request status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ApprovalRequest(Base):
    """Approval request model"""
    __tablename__ = "approval_requests"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    request_type = Column(String(50), nullable=False)  # Use String to match DB constraint (lowercase)
    artifact_id = Column(PGUUID(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=True)
    prompt_id = Column(PGUUID(as_uuid=True), ForeignKey("prompts.id", ondelete="CASCADE"), nullable=True)
    task_id = Column(PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    plan_id = Column(PGUUID(as_uuid=True), ForeignKey("plans.id", ondelete="CASCADE"), nullable=True)
    
    # Request data
    request_data = Column(JSON, nullable=False)
    risk_assessment = Column(JSON, nullable=True)
    recommendation = Column(Text, nullable=True)
    
    # Status
    status = Column(String(50), nullable=False, default="pending")  # Use String to match DB constraint (lowercase)
    required_action = Column(String(20), nullable=True)
    
    # Feedback
    human_feedback = Column(Text, nullable=True)
    approved_by = Column(String(255), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    decision_timeout = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    artifact = relationship("Artifact", backref="approval_requests")
    prompt = relationship("Prompt", backref="approval_requests")
    task = relationship("Task", backref="approval_requests")
    plan = relationship("Plan", backref="approval_requests")
    
    def __repr__(self):
        return f"<ApprovalRequest(id={self.id}, type={self.request_type}, status={self.status})>"

