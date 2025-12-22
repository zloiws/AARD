"""
API routes for current work (active tasks) real-time monitoring
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/current-work", tags=["current-work"])


class ActiveStep(BaseModel):
    """Active step in execution"""
    step_id: str
    step_number: int
    description: str
    status: str
    progress: Optional[float] = None
    started_at: Optional[str] = None


class ActiveTask(BaseModel):
    """Active task with real-time progress"""
    task_id: UUID
    description: str
    status: str
    created_at: str
    updated_at: str
    
    current_stage: str  # planning, executing, etc.
    progress_percent: float
    
    plan_version: Optional[int] = None
    current_step: Optional[ActiveStep] = None
    total_steps: int = 0
    completed_steps: int = 0
    
    latest_logs: List[Dict[str, Any]] = []
    
    agents_in_use: List[str] = []
    tools_in_use: List[str] = []


class CurrentWorkResponse(BaseModel):
    """Response with all active tasks"""
    tasks: List[ActiveTask] = []
    total: int = 0


@router.get("/tasks", response_model=CurrentWorkResponse)
async def get_active_tasks(
    include_all: bool = False,
    db: Session = Depends(get_db)
):
    """Get all currently active tasks with real-time progress
    
    Args:
        include_all: If True, return all tasks (including completed/failed). 
                     If False, return only active tasks.
    """
    if include_all:
        # Get all tasks
        tasks = db.query(Task).order_by(Task.updated_at.desc()).all()
    else:
        # Get active tasks (planning, in_progress, pending_approval)
        active_statuses = [
            TaskStatus.PLANNING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.PENDING_APPROVAL,
            TaskStatus.EXECUTING,
            TaskStatus.PAUSED
        ]
        
        tasks = db.query(Task).filter(
            Task.status.in_(active_statuses)
        ).order_by(Task.updated_at.desc()).all()
    
    active_tasks = []
    
    for task in tasks:
        context = task.get_context()
        
        # Get current plan
        plan = None
        if task.plan_id:
            plan = db.query(Plan).filter(Plan.id == task.plan_id).first()
        elif task.plans:  # Using backref
            plan = max(task.plans, key=lambda p: p.version) if task.plans else None
        
        # Determine current stage based on status
        current_stage = "planning"
        if task.status == TaskStatus.IN_PROGRESS or task.status == TaskStatus.EXECUTING:
            current_stage = "executing"
        elif task.status == TaskStatus.PENDING_APPROVAL:
            current_stage = "pending_approval"
        elif task.status == TaskStatus.PLANNING:
            current_stage = "planning"
        elif task.status == TaskStatus.COMPLETED:
            current_stage = "completed"
        elif task.status == TaskStatus.FAILED:
            current_stage = "failed"
        
        # Get progress
        total_steps = 0
        completed_steps = 0
        current_step_data = None
        
        if plan and plan.steps:
            total_steps = len(plan.steps)
            for i, step in enumerate(plan.steps):
                step_status = step.get("status", "pending")
                if step_status == "completed":
                    completed_steps += 1
                elif step_status == "in_progress" or (i == plan.current_step and step_status == "pending"):
                    current_step_data = ActiveStep(
                        step_id=step.get("step_id", f"step_{i}"),
                        step_number=i + 1,
                        description=step.get("description", ""),
                        status=step_status,
                        started_at=step.get("started_at")
                    )
        
        progress_percent = (completed_steps / total_steps * 100) if total_steps > 0 else 0
        
        # Get latest logs from context (last 10)
        model_logs = context.get("model_logs", [])
        latest_logs = []
        if model_logs:
            # Get last 10 logs
            sorted_logs = sorted(
                [log for log in model_logs if isinstance(log, dict)],
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:10]
            latest_logs = [
                {
                    "timestamp": log.get("timestamp", ""),
                    "stage": log.get("stage", log.get("type", "unknown")),
                    "model": log.get("model", ""),
                    "content_preview": str(log.get("content", ""))[:200]
                }
                for log in sorted_logs
            ]
        
        # Get agents/tools in use from context
        agent_selection = context.get("agent_selection", {})
        tool_selection = context.get("tool_selection", {})
        
        agents_in_use = [agent.get("name", "") for agent in agent_selection.get("selected_agents", [])]
        tools_in_use = [tool.get("name", "") for tool in tool_selection.get("selected_tools", [])]
        
        active_task = ActiveTask(
            task_id=task.id,
            description=task.description,
            status=task.status,
            created_at=task.created_at.isoformat() if task.created_at else "",
            updated_at=task.updated_at.isoformat() if task.updated_at else "",
            current_stage=current_stage,
            progress_percent=progress_percent,
            plan_version=plan.version if plan else None,
            current_step=current_step_data,
            total_steps=total_steps,
            completed_steps=completed_steps,
            latest_logs=latest_logs,
            agents_in_use=agents_in_use,
            tools_in_use=tools_in_use
        )
        
        active_tasks.append(active_task)
    
    return CurrentWorkResponse(
        tasks=active_tasks,
        total=len(active_tasks)
    )


@router.get("/task/{task_id}", response_model=ActiveTask)
async def get_active_task_details(
    task_id: UUID,
    include_all: bool = False,
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific task
    
    Args:
        include_all: If True, return task regardless of status. 
                     If False, only return active tasks.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    # Check if task is active (only if include_all is False)
    if not include_all:
        active_statuses = [
            TaskStatus.PLANNING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.PENDING_APPROVAL,
            TaskStatus.EXECUTING,
            TaskStatus.PAUSED
        ]
        
        if task.status not in active_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Task {task_id} is not active (status: {task.status}). Use ?include_all=true to get all tasks."
            )
    
    # Reuse logic from get_active_tasks
    context = task.get_context()
    
    plan = None
    if task.plan_id:
        plan = db.query(Plan).filter(Plan.id == task.plan_id).first()
    elif task.plans:
        plan = max(task.plans, key=lambda p: p.version) if task.plans else None
    
    # Determine current stage based on status
    current_stage = "planning"
    if task.status == TaskStatus.IN_PROGRESS or task.status == TaskStatus.EXECUTING:
        current_stage = "executing"
    elif task.status == TaskStatus.PENDING_APPROVAL:
        current_stage = "pending_approval"
    elif task.status == TaskStatus.PLANNING:
        current_stage = "planning"
    elif task.status == TaskStatus.COMPLETED:
        current_stage = "completed"
    elif task.status == TaskStatus.FAILED:
        current_stage = "failed"
    
    total_steps = 0
    completed_steps = 0
    current_step_data = None
    
    if plan and plan.steps:
        total_steps = len(plan.steps)
        for i, step in enumerate(plan.steps):
            step_status = step.get("status", "pending")
            if step_status == "completed":
                completed_steps += 1
            elif step_status == "in_progress" or (i == plan.current_step and step_status == "pending"):
                current_step_data = ActiveStep(
                    step_id=step.get("step_id", f"step_{i}"),
                    step_number=i + 1,
                    description=step.get("description", ""),
                    status=step_status,
                    started_at=step.get("started_at")
                )
    
    progress_percent = (completed_steps / total_steps * 100) if total_steps > 0 else 0
    
    # Get all logs (not just last 10)
    model_logs = context.get("model_logs", [])
    latest_logs = []
    if model_logs:
        sorted_logs = sorted(
            [log for log in model_logs if isinstance(log, dict)],
            key=lambda x: x.get("timestamp", "")
        )
        latest_logs = [
            {
                "timestamp": log.get("timestamp", ""),
                "stage": log.get("stage", log.get("type", "unknown")),
                "model": log.get("model", ""),
                "content": log.get("content", ""),
                "metadata": log.get("metadata", {})
            }
            for log in sorted_logs
        ]
    
    agent_selection = context.get("agent_selection", {})
    tool_selection = context.get("tool_selection", {})
    
    agents_in_use = [agent.get("name", "") for agent in agent_selection.get("selected_agents", [])]
    tools_in_use = [tool.get("name", "") for tool in tool_selection.get("selected_tools", [])]
    
    return ActiveTask(
        task_id=task.id,
        description=task.description,
        status=task.status,
        created_at=task.created_at.isoformat() if task.created_at else "",
        updated_at=task.updated_at.isoformat() if task.updated_at else "",
        current_stage=current_stage,
        progress_percent=progress_percent,
        plan_version=plan.version if plan else None,
        current_step=current_step_data,
        total_steps=total_steps,
        completed_steps=completed_steps,
        latest_logs=latest_logs,
        agents_in_use=agents_in_use,
        tools_in_use=tools_in_use
    )

