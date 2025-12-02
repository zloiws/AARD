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
    status: str = None,
    db: Session = Depends(get_db)
):
    """Approval queue page with statistics and filters"""
    service = ApprovalService(db)
    
    # Get statistics
    stats = service.get_approval_statistics()
    
    # Parse filters
    approval_type = None
    if request_type:
        try:
            approval_type = ApprovalRequestType(request_type)
        except ValueError:
            approval_type = None
    
    # Get approvals based on filters
    if status == "all" or status is None:
        # Show all if status is "all" or not specified, but default to pending
        if status == "all":
            approvals = service.get_all_requests(
                request_type=request_type,
                limit=100
            )
        else:
            # Default: show pending
            approvals = service.get_pending_requests(limit=100, request_type=approval_type)
    else:
        approvals = service.get_all_requests(
            status=status,
            request_type=request_type,
            limit=100
        )
    
    return templates.TemplateResponse(
        "approvals/queue.html",
        {
            "request": request,
            "approvals": approvals,
            "statistics": stats,
            "current_filter_type": request_type,
            "current_filter_status": status or "pending"
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
    
    # Get related plan if this is a plan approval
    plan = None
    if approval.plan_id:
        from app.services.planning_service import PlanningService
        planning_service = PlanningService(db)
        plan = planning_service.get_plan(approval.plan_id)
    
    return templates.TemplateResponse(
        "approvals/detail.html",
        {
            "request": request,
            "approval": approval,
            "plan": plan  # Pass related plan
        }
    )

