"""
Approval service for managing approval requests
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.approval import (
    ApprovalRequest,
    ApprovalRequestType,
    ApprovalRequestStatus,
)
from app.models.artifact import Artifact, ArtifactStatus
from app.models.prompt import Prompt, PromptStatus
from app.models.plan import Plan, PlanStatus


class ApprovalService:
    """Service for managing approval requests"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_approval_request(
        self,
        request_type: ApprovalRequestType,
        request_data: Dict[str, Any],
        artifact_id: Optional[UUID] = None,
        prompt_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        plan_id: Optional[UUID] = None,
        risk_assessment: Optional[Dict[str, Any]] = None,
        recommendation: Optional[str] = None,
        timeout_hours: int = 24
    ) -> ApprovalRequest:
        """Create a new approval request"""
        
        approval = ApprovalRequest(
            request_type=request_type.value.lower() if hasattr(request_type, 'value') else str(request_type).lower(),
            artifact_id=artifact_id,
            prompt_id=prompt_id,
            task_id=task_id,
            plan_id=plan_id,
            request_data=request_data,
            risk_assessment=risk_assessment,
            recommendation=recommendation,
            status="pending",  # Use lowercase to match DB constraint
            decision_timeout=datetime.now(timezone.utc) + timedelta(hours=timeout_hours)
        )
        
        self.db.add(approval)
        self.db.commit()
        self.db.refresh(approval)
        
        return approval
    
    def get_approval_request(self, request_id: UUID) -> Optional[ApprovalRequest]:
        """Get approval request by ID"""
        return self.db.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id
        ).first()
    
    def approve_request(
        self,
        request_id: UUID,
        approved_by: str,
        feedback: Optional[str] = None
    ) -> ApprovalRequest:
        """Approve an approval request"""
        
        approval = self.get_approval_request(request_id)
        
        if not approval:
            raise ValueError(f"Approval request {request_id} not found")
        
        if approval.status != "pending":
            raise ValueError(f"Approval request {request_id} is not pending")
        
        approval.status = "approved"  # Use lowercase to match DB constraint
        approval.approved_by = approved_by
        approval.approved_at = datetime.utcnow()
        if feedback:
            approval.human_feedback = feedback
        
        # Learn from feedback using FeedbackLearningService
        try:
            from app.services.feedback_learning_service import FeedbackLearningService
            feedback_learning = FeedbackLearningService(self.db)
            feedback_learning.learn_from_approval_feedback(approval, feedback)
        except Exception as e:
            from app.core.logging_config import LoggingConfig
            logger = LoggingConfig.get_logger(__name__)
            logger.warning(f"Failed to learn from approval feedback: {e}", exc_info=True)
        
        # Apply the approval based on type (compare lowercase values)
        request_type_lower = approval.request_type.lower()
        if request_type_lower == "new_artifact":
            self._activate_artifact(approval.artifact_id)
        elif request_type_lower == "artifact_update":
            self._update_artifact(approval.artifact_id, approval.request_data)
        elif request_type_lower == "prompt_change":
            self._update_prompt(approval.prompt_id, approval.request_data)
        elif request_type_lower == "plan_approval":
            self._approve_plan(approval.plan_id, approval.request_data)
        
        self.db.commit()
        self.db.refresh(approval)
        
        return approval
    
    def reject_request(
        self,
        request_id: UUID,
        rejected_by: str,
        feedback: str
    ) -> ApprovalRequest:
        """Reject an approval request"""
        
        approval = self.get_approval_request(request_id)
        
        if not approval:
            raise ValueError(f"Approval request {request_id} not found")
        
        approval.status = "rejected"  # Use lowercase to match DB constraint
        approval.rejected_by = rejected_by
        approval.rejected_at = datetime.utcnow()
        approval.human_feedback = feedback
        
        # Learn from feedback using FeedbackLearningService
        try:
            from app.services.feedback_learning_service import FeedbackLearningService
            feedback_learning = FeedbackLearningService(self.db)
            feedback_learning.learn_from_approval_feedback(approval, feedback)
        except Exception as e:
            from app.core.logging_config import LoggingConfig
            logger = LoggingConfig.get_logger(__name__)
            logger.warning(f"Failed to learn from rejection feedback: {e}", exc_info=True)
        
        self.db.commit()
        self.db.refresh(approval)
        
        return approval
    
    def modify_request(
        self,
        request_id: UUID,
        modified_by: str,
        modified_data: Dict[str, Any],
        feedback: Optional[str] = None
    ) -> ApprovalRequest:
        """Modify an approval request (user made changes)"""
        
        approval = self.get_approval_request(request_id)
        
        if not approval:
            raise ValueError(f"Approval request {request_id} not found")
        
        approval.status = "modified"  # Use lowercase to match DB constraint
        approval.request_data = {**approval.request_data, **modified_data}
        approval.approved_by = modified_by
        approval.approved_at = datetime.utcnow()
        if feedback:
            approval.human_feedback = feedback
        
        self.db.commit()
        self.db.refresh(approval)
        
        return approval
    
    def get_pending_requests(
        self,
        limit: int = 50,
        request_type: Optional[ApprovalRequestType] = None
    ) -> List[ApprovalRequest]:
        """Get pending approval requests"""
        
        query = self.db.query(ApprovalRequest).filter(
            ApprovalRequest.status == "pending"  # Use lowercase
        )
        
        if request_type:
            request_type_str = request_type.value.lower() if hasattr(request_type, 'value') else str(request_type).lower()
            query = query.filter(ApprovalRequest.request_type == request_type_str)
        
        return query.order_by(ApprovalRequest.created_at.desc()).limit(limit).all()
    
    def get_requests_by_artifact(self, artifact_id: UUID) -> List[ApprovalRequest]:
        """Get all approval requests for an artifact"""
        return self.db.query(ApprovalRequest).filter(
            ApprovalRequest.artifact_id == artifact_id
        ).order_by(ApprovalRequest.created_at.desc()).all()
    
    def get_requests_by_prompt(self, prompt_id: UUID) -> List[ApprovalRequest]:
        """Get all approval requests for a prompt"""
        return self.db.query(ApprovalRequest).filter(
            ApprovalRequest.prompt_id == prompt_id
        ).order_by(ApprovalRequest.created_at.desc()).all()
    
    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get statistics about approval requests"""
        from sqlalchemy import func
        
        total = self.db.query(func.count(ApprovalRequest.id)).scalar() or 0
        pending = self.db.query(func.count(ApprovalRequest.id)).filter(
            ApprovalRequest.status == "pending"
        ).scalar() or 0
        approved = self.db.query(func.count(ApprovalRequest.id)).filter(
            ApprovalRequest.status == "approved"
        ).scalar() or 0
        rejected = self.db.query(func.count(ApprovalRequest.id)).filter(
            ApprovalRequest.status == "rejected"
        ).scalar() or 0
        
        # Count by type
        type_counts = {}
        for req_type in ApprovalRequestType:
            count = self.db.query(func.count(ApprovalRequest.id)).filter(
                ApprovalRequest.request_type == req_type.value.lower()
            ).scalar() or 0
            type_counts[req_type.value] = count
        
        # Count urgent (expiring soon)
        now = datetime.now(timezone.utc)
        urgent = self.db.query(func.count(ApprovalRequest.id)).filter(
            and_(
                ApprovalRequest.status == "pending",
                ApprovalRequest.decision_timeout.isnot(None),
                ApprovalRequest.decision_timeout <= now + timedelta(hours=2)
            )
        ).scalar() or 0
        
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "urgent": urgent,
            "by_type": type_counts
        }
    
    def get_all_requests(
        self,
        status: Optional[str] = None,
        request_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ApprovalRequest]:
        """Get all approval requests with optional filters"""
        query = self.db.query(ApprovalRequest)
        
        if status:
            query = query.filter(ApprovalRequest.status == status.lower())
        
        if request_type:
            query = query.filter(ApprovalRequest.request_type == request_type.lower())
        
        return query.order_by(ApprovalRequest.created_at.desc()).offset(offset).limit(limit).all()
    
    def _activate_artifact(self, artifact_id: Optional[UUID]):
        """Activate an artifact after approval"""
        if not artifact_id:
            return
        artifact = self.db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if artifact:
            artifact.status = "active"  # Use lowercase to match DB constraint
            self.db.commit()
    
    def _update_artifact(self, artifact_id: Optional[UUID], request_data: Dict[str, Any]):
        """Update an artifact after approval"""
        if not artifact_id:
            return
        artifact = self.db.query(Artifact).filter(Artifact.id == artifact_id).first()
        if artifact:
            if "code" in request_data:
                artifact.code = request_data["code"]
            if "prompt" in request_data:
                artifact.prompt = request_data["prompt"]
            if "description" in request_data:
                artifact.description = request_data["description"]
            artifact.version += 1
            artifact.status = "active"  # Use lowercase to match DB constraint
            self.db.commit()
    
    def _update_prompt(self, prompt_id: Optional[UUID], request_data: Dict[str, Any]):
        """Update a prompt after approval"""
        if not prompt_id:
            return
        prompt = self.db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if prompt:
            if "prompt_text" in request_data:
                prompt.prompt_text = request_data["prompt_text"]
            if "name" in request_data:
                prompt.name = request_data["name"]
            prompt.version += 1
            prompt.status = PromptStatus.ACTIVE
            prompt.last_improved_at = datetime.utcnow()
            self.db.commit()
    
    def _approve_plan(self, plan_id: Optional[UUID], request_data: Dict[str, Any]):
        """Approve a plan after approval"""
        if not plan_id:
            # Fallback: try to get from request_data
            plan_id = request_data.get("plan_id")
            if not plan_id:
                return
        
        plan = self.db.query(Plan).filter(Plan.id == plan_id).first()
        if plan:
            plan.status = "approved"  # Use lowercase string to match DB constraint
            plan.approved_at = datetime.utcnow()
            self.db.commit()

