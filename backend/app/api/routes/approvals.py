"""
API routes for approval requests
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.approval import ApprovalRequest, ApprovalRequestType, ApprovalRequestStatus
from app.services.approval_service import ApprovalService


router = APIRouter(prefix="/api/approvals", tags=["approvals"])


class ApprovalResponse(BaseModel):
    """Approval request response model"""
    id: UUID
    request_type: str
    status: str
    artifact_id: Optional[UUID] = None
    prompt_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    recommendation: Optional[str] = None
    risk_assessment: Optional[dict] = None
    created_at: datetime  # FastAPI автоматически сериализует datetime в ISO формат
    decision_timeout: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ApproveRequest(BaseModel):
    """Request model for approving"""
    feedback: Optional[str] = None


class RejectRequest(BaseModel):
    """Request model for rejecting"""
    feedback: str = Field(..., description="Reason for rejection")


class ModifyRequest(BaseModel):
    """Request model for modifying"""
    modified_data: dict = Field(..., description="Modified data")
    feedback: Optional[str] = None


@router.get("/", response_model=List[ApprovalResponse])
async def get_pending_approvals(
    request_type: Optional[ApprovalRequestType] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get pending approval requests"""
    try:
        service = ApprovalService(db)
        approvals = service.get_pending_requests(limit=limit, request_type=request_type)
        return approvals
    except Exception as e:
        import traceback
        error_detail = f"Error getting approvals: {str(e)}\n{traceback.format_exc()}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )


@router.get("/{request_id}", response_model=ApprovalResponse)
async def get_approval_request(
    request_id: UUID,
    db: Session = Depends(get_db)
):
    """Get approval request by ID"""
    service = ApprovalService(db)
    approval = service.get_approval_request(request_id)
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {request_id} not found"
        )
    
    return approval


@router.post("/{request_id}/approve")
async def approve_request(
    request_id: UUID,
    request: ApproveRequest,
    db: Session = Depends(get_db)
):
    """Approve an approval request"""
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi import Request as FastAPIRequest
    
    service = ApprovalService(db)
    
    try:
        approval = service.approve_request(
            request_id=request_id,
            approved_by="user",  # TODO: Get from auth
            feedback=request.feedback
        )
        
        # Check if request is from HTMX
        # For now, return JSON - HTMX will handle it
        return {"status": "approved", "approval_id": str(approval.id), "message": "Утверждение успешно обработано"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/reject")
async def reject_request(
    request_id: UUID,
    request: RejectRequest,
    db: Session = Depends(get_db)
):
    """Reject an approval request"""
    service = ApprovalService(db)
    
    try:
        approval = service.reject_request(
            request_id=request_id,
            rejected_by="user",  # TODO: Get from auth
            feedback=request.feedback
        )
        return {"status": "rejected", "approval_id": str(approval.id), "message": "Запрос отклонен"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{request_id}/modify")
async def modify_request(
    request_id: UUID,
    request: ModifyRequest,
    db: Session = Depends(get_db)
):
    """Modify an approval request"""
    service = ApprovalService(db)
    
    try:
        approval = service.modify_request(
            request_id=request_id,
            modified_by="user",  # TODO: Get from auth
            modified_data=request.modified_data,
            feedback=request.feedback
        )
        return {"status": "modified", "approval_id": str(approval.id)}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/artifact/{artifact_id}", response_model=List[ApprovalResponse])
async def get_artifact_approvals(
    artifact_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all approval requests for an artifact"""
    service = ApprovalService(db)
    approvals = service.get_requests_by_artifact(artifact_id)
    return approvals


@router.get("/prompt/{prompt_id}", response_model=List[ApprovalResponse])
async def get_prompt_approvals(
    prompt_id: UUID,
    db: Session = Depends(get_db)
):
    """Get all approval requests for a prompt"""
    service = ApprovalService(db)
    approvals = service.get_requests_by_prompt(prompt_id)
    return approvals

