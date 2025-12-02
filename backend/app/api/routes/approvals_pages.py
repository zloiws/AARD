"""
Web pages for approval requests
"""
from typing import List
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.core.database import get_db
from app.services.approval_service import ApprovalService
from app.models.approval import ApprovalRequestType

router = APIRouter(tags=["approvals_pages"])


@router.get("/approvals", response_class=HTMLResponse)
async def approvals_queue(
    request: Request,
    request_type: str = None,
    db: Session = Depends(get_db)
):
    """Approval queue page"""
    service = ApprovalService(db)
    
    # Parse request type if provided
    approval_type = None
    if request_type:
        try:
            approval_type = ApprovalRequestType(request_type)
        except ValueError:
            approval_type = None
    
    approvals = service.get_pending_requests(limit=100, request_type=approval_type)
    
    return templates.TemplateResponse(
        "approvals/queue.html",
        {
            "request": request,
            "approvals": approvals
        }
    )


@router.get("/approvals/{approval_id}", response_class=HTMLResponse)
async def approval_detail(
    request: Request,
    approval_id: UUID,
    db: Session = Depends(get_db)
):
    """Approval detail page"""
    service = ApprovalService(db)
    approval = service.get_approval_request(approval_id)
    
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval request {approval_id} not found"
        )
    
    return templates.TemplateResponse(
        "approvals/detail.html",
        {
            "request": request,
            "approval": approval
        }
    )

