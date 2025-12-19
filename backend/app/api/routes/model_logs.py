"""
API routes for model logs from Digital Twin context
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.database import get_db
from app.models.plan import Plan
from app.models.task import Task
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/model-logs", tags=["model-logs"])


class ModelLogEntry(BaseModel):
    """Model log entry"""
    type: str  # 'request', 'response', 'thinking', 'error'
    model: str
    content: Any
    metadata: Dict[str, Any] = {}
    timestamp: str


class ModelLogsResponse(BaseModel):
    """Model logs response"""
    task_id: Optional[UUID] = None
    logs: List[ModelLogEntry] = []
    total: int = 0


@router.get("/task/{task_id}", response_model=ModelLogsResponse)
async def get_model_logs_for_task(
    task_id: UUID,
    db: Session = Depends(get_db)
):
    """Get model logs from Digital Twin context for a task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    context = task.get_context()
    model_logs = context.get("model_logs", [])
    
    # Convert to response format
    log_entries = [
        ModelLogEntry(**log) for log in model_logs if isinstance(log, dict)
    ]
    
    return ModelLogsResponse(
        task_id=task_id,
        logs=log_entries,
        total=len(log_entries)
    )


@router.get("/latest", response_model=ModelLogsResponse)
async def get_latest_model_logs(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get latest model logs from all tasks"""
    # Get recent tasks with model logs
    tasks = db.query(Task).order_by(Task.created_at.desc()).limit(50).all()
    
    all_logs = []
    for task in tasks:
        context = task.get_context()
        model_logs = context.get("model_logs", [])
        
        for log in model_logs:
            if isinstance(log, dict):
                log_entry = ModelLogEntry(**log)
                all_logs.append(log_entry)
    
    # Sort by timestamp (newest first)
    all_logs.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Limit
    all_logs = all_logs[:limit]
    
    return ModelLogsResponse(
        logs=all_logs,
        total=len(all_logs)
    )


# Pydantic models for summary with branching
class BranchingSummary(BaseModel):
    """Summary with all branches"""
    task_id: UUID
    task_description: str
    status: str
    
    user_request: Optional[str] = None
    request_analysis: Optional[Dict[str, Any]] = None
    
    plans: List[Dict[str, Any]] = []
    plans_alternatives: List[Dict[str, Any]] = []
    replanning_history: List[Dict[str, Any]] = []
    
    agents_available: List[Dict[str, Any]] = []
    agents_selected: List[Dict[str, Any]] = []
    
    prompts_used: List[Dict[str, Any]] = []
    
    tools_available: List[Dict[str, Any]] = []
    tools_used: List[Dict[str, Any]] = []
    
    memory_storage: Dict[str, Any] = {}
    
    what_was_done: List[str] = []
    what_was_not_done: List[Dict[str, Any]] = []
    
    timeline: List[Dict[str, Any]] = []


# Helper function for summary (will be called by both endpoints)
async def _get_task_summary(task_id: UUID, db: Session) -> BranchingSummary:
    """Internal helper to get task summary with branching"""
    task = db.query(Task).filter(Task.id == task_id).first()
    
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    context = task.get_context()
    
    # Get all plans for this task
    plans = db.query(Plan).filter(Plan.task_id == task_id).order_by(Plan.version).all()
    
    plans_data = []
    plans_alternatives = []
    replanning_history = []
    
    for plan in plans:
        plan_data = {
            "id": str(plan.id),
            "version": plan.version,
            "status": plan.status,
            "goal": plan.goal,
            "strategy": plan.strategy,
            "steps_count": len(plan.steps) if plan.steps else 0,
            "created_at": plan.created_at.isoformat() if plan.created_at else None
        }
        plans_data.append(plan_data)
        
        # Get alternatives
        if plan.alternatives:
            plans_alternatives.extend([
                {
                    "plan_version": plan.version,
                    "alternative": alt,
                    "reason": alt.get("reason", "Not specified")
                }
                for alt in (plan.alternatives if isinstance(plan.alternatives, list) else [])
            ])
    
    # Build replanning history from context
    planning_decisions = context.get("planning_decisions", {})
    if isinstance(planning_decisions, dict) and "replanning_history" in planning_decisions:
        replanning_history = planning_decisions["replanning_history"]
    elif len(plans_data) > 1:
        # Infer replanning history from plan versions
        for i in range(1, len(plans_data)):
            replanning_history.append({
                "from_version": plans_data[i-1]["version"],
                "to_version": plans_data[i]["version"],
                "reason": f"Plan updated from version {plans_data[i-1]['version']} to {plans_data[i]['version']}",
                "timestamp": plans_data[i].get("created_at")
            })
    
    # Extract from context
    user_request = context.get("original_user_request", task.description)
    request_analysis = context.get("request_analysis", {})
    
    # Get agent/prompt/tool information from context
    agent_selection = context.get("agent_selection", {})
    prompt_usage = context.get("prompt_usage", {})
    tool_selection = context.get("tool_selection", {})
    memory_storage = context.get("memory_storage", {})
    
    agents_available = agent_selection.get("available_agents", []) if isinstance(agent_selection, dict) else []
    agents_selected = agent_selection.get("selected_agents", []) if isinstance(agent_selection, dict) else []
    
    prompts_used = prompt_usage.get("prompts_used", []) if isinstance(prompt_usage, dict) else []
    
    tools_available = tool_selection.get("available_tools", []) if isinstance(tool_selection, dict) else []
    tools_used = tool_selection.get("selected_tools", []) if isinstance(tool_selection, dict) else []
    
    # Get model logs to build timeline
    model_logs = context.get("model_logs", [])
    timeline = []
    
    for log in model_logs:
        if isinstance(log, dict):
            stage = log.get("stage", log.get("type", "unknown"))
            timeline.append({
                "timestamp": log.get("timestamp", ""),
                "event_type": stage,
                "data": {
                    "model": log.get("model", ""),
                    "content": log.get("content", ""),
                    "metadata": log.get("metadata", {})
                }
            })
    
    # Sort timeline by timestamp
    timeline.sort(key=lambda x: x.get("timestamp", ""))
    
    # Determine what was done and what was not
    what_was_done = []
    what_was_not_done = []
    
    # Get active plan
    active_plan = None
    if task.plan_id:
        active_plan = db.query(Plan).filter(Plan.id == task.plan_id).first()
    elif plans:
        active_plan = max(plans, key=lambda p: p.version)
    
    if active_plan and active_plan.steps:
        for i, step in enumerate(active_plan.steps):
            step_status = step.get("status", "pending")
            if step_status == "completed":
                what_was_done.append(f"Шаг {i+1}: {step.get('description', 'N/A')}")
            elif step_status == "failed":
                what_was_not_done.append({
                    "step": f"Шаг {i+1}: {step.get('description', 'N/A')}",
                    "reason": step.get("error", "Шаг не выполнен")
                })
            elif step_status == "pending" and task.status in ["completed", "failed", "cancelled"]:
                what_was_not_done.append({
                    "step": f"Шаг {i+1}: {step.get('description', 'N/A')}",
                    "reason": f"Задача завершена со статусом {task.status}"
                })
    
    return BranchingSummary(
        task_id=task.id,
        task_description=task.description,
        status=task.status,
        user_request=user_request,
        request_analysis=request_analysis,
        plans=plans_data,
        plans_alternatives=plans_alternatives,
        replanning_history=replanning_history,
        agents_available=agents_available,
        agents_selected=agents_selected,
        prompts_used=prompts_used,
        tools_available=tools_available,
        tools_used=tools_used,
        memory_storage=memory_storage,
        what_was_done=what_was_done,
        what_was_not_done=what_was_not_done,
        timeline=timeline
    )


@router.get("/summaries/latest")
async def get_latest_summaries(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get latest task summaries with branching information"""
    # Get recent completed or failed tasks
    tasks = db.query(Task).filter(
        Task.status.in_(["completed", "failed", "cancelled"])
    ).order_by(Task.updated_at.desc()).limit(limit).all()
    
    summaries = []
    for task in tasks:
        summary = await _get_task_summary(task.id, db)
        summaries.append(summary)
    
    return {"summaries": summaries, "total": len(summaries)}


@router.get("/summary/{task_id}", response_model=BranchingSummary)
async def get_task_summary_with_branching(
    task_id: UUID,
    db: Session = Depends(get_db)
):
    """Get brief summary with all branches for a task"""
    return await _get_task_summary(task_id, db)

