"""
API routes for dashboard
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.core.database import get_db
from app.core.templates import templates
from app.models.task import Task, TaskStatus
from app.models.plan import Plan
from app.models.approval import ApprovalRequest
from app.services.interactive_execution_service import InteractiveExecutionService

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard/tasks")
async def get_dashboard_tasks(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get tasks for dashboard
    
    Supports both JSON and HTML responses:
    - JSON: for API clients
    - HTML: for HTMX requests (returns HTML fragment)
    
    Args:
        request: FastAPI request object
        status: Optional status filter (in_progress, pending_approval, etc.)
        db: Database session
        
    Returns:
        HTML fragment if Accept header contains text/html, otherwise JSON
    """
    try:
        # Build query
        query = db.query(Task)
        
        # Filter by status if provided
        if status:
            try:
                task_status = TaskStatus(status)
                query = query.filter(Task.status == task_status)
            except ValueError:
                pass  # Invalid status, ignore filter
        
        # Get active tasks (in progress, pending approval, on hold)
        active_statuses = [
            TaskStatus.IN_PROGRESS,
            TaskStatus.PENDING_APPROVAL,
            TaskStatus.ON_HOLD,
            TaskStatus.EXECUTING  # Legacy
        ]
        active_tasks = query.filter(
            Task.status.in_(active_statuses)
        ).order_by(Task.updated_at.desc()).limit(50).all()
        
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
        
        # Check if request wants HTML (HTMX request)
        accept_header = request.headers.get("accept", "")
        if "text/html" in accept_header or request.headers.get("HX-Request") == "true":
            # Return HTML fragment for HTMX
            if not tasks_data:
                return HTMLResponse("<div class='text-center py-5'><p class='text-muted'>Нет активных задач</p></div>")
            
            return templates.TemplateResponse(
                "dashboard_tasks_fragment.html",
                {
                    "request": request,
                    "tasks": tasks_data
                }
            )
        
        # Return JSON for API clients
        return JSONResponse({
            "tasks": [
                {
                    **task_dict,
                    "created_at": task_dict["created_at"].isoformat() if task_dict["created_at"] else None,
                    "updated_at": task_dict["updated_at"].isoformat() if task_dict["updated_at"] else None,
                }
                for task_dict in tasks_data
            ]
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard tasks: {str(e)}")


@router.get("/api/dashboard/plan-history/{plan_id}")
async def get_plan_history(
    plan_id: UUID,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get plan change history from episodic memory
    
    Args:
        plan_id: Plan ID
        db: Database session
        
    Returns:
        Plan history events
    """
    try:
        from app.services.memory_service import MemoryService
        from app.models.agent_memory import MemoryType
        
        # Get plan
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Get agent_id from plan
        agent_id = None
        if plan.agent_metadata and isinstance(plan.agent_metadata, dict):
            agent_id_str = plan.agent_metadata.get("agent_id")
            if agent_id_str:
                try:
                    agent_id = UUID(agent_id_str)
                except (ValueError, TypeError):
                    pass
        
        if not agent_id:
            return {"history": []}
        
        # Search episodic memory for plan history
        memory_service = MemoryService(db)
        memories = memory_service.search_memories(
            agent_id=agent_id,
            content_query={"plan_id": str(plan_id)},
            memory_type=MemoryType.EXPERIENCE.value,
            limit=50
        )
        
        # Format history
        history = []
        for memory in memories:
            if memory.content and memory.content.get("plan_id") == str(plan_id):
                history.append({
                    "event_type": memory.content.get("event_type", "unknown"),
                    "timestamp": memory.created_at.isoformat() if memory.created_at else None,
                    "plan_version": memory.content.get("plan_version", 0),
                    "context": memory.content
                })
        
        # Sort by timestamp
        history.sort(key=lambda x: x["timestamp"] or "", reverse=True)
        
        return {"history": history}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching plan history: {str(e)}")


@router.post("/api/dashboard/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: UUID,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Cancel a task
    
    Args:
        task_id: Task ID
        db: Database session
        
    Returns:
        Success message
    """
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Only allow cancellation of active tasks
        if task.status not in [TaskStatus.IN_PROGRESS, TaskStatus.EXECUTING, TaskStatus.PENDING_APPROVAL, TaskStatus.ON_HOLD]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task with status {task.status.value}"
            )
        
        # Update task status
        task.status = TaskStatus.CANCELLED
        db.commit()
        db.refresh(task)
        
        # Cancel any active plans
        active_plans = db.query(Plan).filter(
            and_(
                Plan.task_id == task_id,
                Plan.status.in_(["executing", "approved"])
            )
        ).all()
        
        for plan in active_plans:
            plan.status = "cancelled"
        
        db.commit()
        
        return {"message": "Task cancelled successfully", "task_id": str(task_id)}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error cancelling task: {str(e)}")


class CreateTaskRequest(BaseModel):
    """Request model for creating a task"""
    description: str
    priority: int = 5
    autonomy_level: int = 2


@router.post("/api/dashboard/tasks/create")
async def create_task_manual(
    request: CreateTaskRequest,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually create a task
    
    Args:
        request: Request body with description, priority, autonomy_level
        db: Database session
        
    Returns:
        Created task
    """
    try:
        description = request.description
        priority = request.priority
        autonomy_level = request.autonomy_level
        
        if not description:
            raise HTTPException(status_code=400, detail="Description is required")
        
        # Validate priority
        if priority < 0 or priority > 9:
            raise HTTPException(status_code=400, detail="Priority must be between 0 and 9")
        
        # Validate autonomy level
        if autonomy_level < 0 or autonomy_level > 4:
            raise HTTPException(status_code=400, detail="Autonomy level must be between 0 and 4")
        
        # Create task
        task = Task(
            description=description,
            status=TaskStatus.DRAFT,
            priority=priority,
            autonomy_level=autonomy_level,
            created_by_role="human"
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return {
            "id": str(task.id),
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority,
            "autonomy_level": task.autonomy_level,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating task: {str(e)}")

