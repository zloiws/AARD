"""
Page routes for dashboard web interface
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.templates import templates
from app.core.database import get_db
from app.models.task import Task, TaskStatus
from app.models.plan import Plan
from app.models.approval import ApprovalRequest

router = APIRouter(tags=["dashboard_pages"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    db: Session = Depends(get_db)
):
    """Dashboard page with active tasks"""
    try:
        # Get active tasks
        active_statuses = [
            TaskStatus.IN_PROGRESS,
            TaskStatus.PENDING_APPROVAL,
            TaskStatus.ON_HOLD,
            TaskStatus.EXECUTING  # Legacy
        ]
        active_tasks = db.query(Task).filter(
            Task.status.in_(active_statuses)
        ).order_by(Task.updated_at.desc()).limit(50).all()
        
        # Get statistics
        total_tasks = db.query(Task).count()
        pending_approval = db.query(Task).filter(Task.status == TaskStatus.PENDING_APPROVAL).count()
        in_progress = db.query(Task).filter(
            or_(
                Task.status == TaskStatus.IN_PROGRESS,
                Task.status == TaskStatus.EXECUTING
            )
        ).count()
        on_hold = db.query(Task).filter(Task.status == TaskStatus.ON_HOLD).count()
        failed = db.query(Task).filter(Task.status == TaskStatus.FAILED).count()
        
        # Get approval requests for pending approval tasks
        pending_approval_tasks = db.query(Task).filter(
            Task.status == TaskStatus.PENDING_APPROVAL
        ).all()
        
        approval_requests_map = {}
        for task in pending_approval_tasks:
            # Get latest plan
            latest_plan = db.query(Plan).filter(
                Plan.task_id == task.id
            ).order_by(Plan.version.desc()).first()
            
            if latest_plan:
                approval_request = db.query(ApprovalRequest).filter(
                    ApprovalRequest.plan_id == latest_plan.id,
                    ApprovalRequest.status == "pending"
                ).first()
                
                if approval_request:
                    approval_requests_map[str(task.id)] = {
                        "id": str(approval_request.id),
                        "plan_id": str(latest_plan.id),
                        "request_data": approval_request.request_data
                    }
        
        # Format tasks with plan information
        tasks_data = []
        for task in active_tasks:
            # Get latest plan for task
            latest_plan = db.query(Plan).filter(
                Plan.task_id == task.id
            ).order_by(Plan.version.desc()).first()
            
            task_dict = {
                "id": str(task.id),
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "created_by_role": task.created_by_role,
                "approved_by_role": task.approved_by_role,
                "autonomy_level": task.autonomy_level,
                "plan": None,
                "approval_request": approval_requests_map.get(str(task.id))
            }
            
            if latest_plan:
                # Calculate progress
                steps = latest_plan.steps if isinstance(latest_plan.steps, list) else []
                total_steps = len(steps)
                current_step = latest_plan.current_step
                progress = (current_step / total_steps * 100) if total_steps > 0 else 0
                
                task_dict["plan"] = {
                    "id": str(latest_plan.id),
                    "version": latest_plan.version,
                    "status": latest_plan.status,
                    "current_step": current_step,
                    "total_steps": total_steps,
                    "progress": progress,
                    "goal": latest_plan.goal
                }
            
            tasks_data.append(task_dict)
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "tasks": tasks_data,
                "statistics": {
                    "total": total_tasks,
                    "pending_approval": pending_approval,
                    "in_progress": in_progress,
                    "on_hold": on_hold,
                    "failed": failed
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading dashboard: {str(e)}")

