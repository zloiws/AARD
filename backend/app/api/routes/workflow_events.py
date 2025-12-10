"""
Workflow Events API routes
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.services.workflow_event_service import WorkflowEventService
from app.models.workflow_event import WorkflowEvent

router = APIRouter(prefix="/api/workflow-events", tags=["workflow-events"])


@router.get("/")
async def get_workflow_events(
    workflow_id: Optional[str] = Query(None, description="Filter by workflow ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    include_entities: bool = Query(False, description="Include related entities (tasks, plans, tools)"),
    db: Session = Depends(get_db)
):
    """
    Get workflow events
    
    Returns events filtered by workflow_id if provided, or all recent events.
    If include_entities=True, also returns related entities (tasks, plans, tools) created during workflow.
    """
    event_service = WorkflowEventService(db)
    
    if workflow_id:
        events = event_service.get_events_by_workflow(workflow_id, limit=limit, offset=offset)
    else:
        events = event_service.get_recent_events(limit=limit, workflow_id=None)
    
    result = {
        "events": [event.to_dict() for event in events],
        "total": len(events),
        "limit": limit,
        "offset": offset
    }
    
    # Include related entities if requested
    if include_entities and workflow_id:
        from app.models.task import Task
        from app.models.plan import Plan
        from app.models.artifact import Artifact
        
        # Get unique entity IDs from events
        task_ids = {e.task_id for e in events if e.task_id}
        plan_ids = {e.plan_id for e in events if e.plan_id}
        tool_ids = {e.tool_id for e in events if e.tool_id}
        
        entities = []
        
        # Get tasks
        if task_ids:
            tasks = db.query(Task).filter(Task.id.in_(task_ids)).all()
            for task in tasks:
                entities.append({
                    "id": str(task.id),
                    "type": "task",
                    "name": task.description or f"Task {str(task.id)[:8]}",
                    "status": task.status,
                })
        
        # Get plans
        if plan_ids:
            plans = db.query(Plan).filter(Plan.id.in_(plan_ids)).all()
            for plan in plans:
                entities.append({
                    "id": str(plan.id),
                    "type": "plan",
                    "name": plan.goal or f"Plan v{plan.version}",
                    "status": plan.status,
                })
        
        # Get tools/artifacts
        if tool_ids:
            tools = db.query(Artifact).filter(Artifact.id.in_(tool_ids)).all()
            for tool in tools:
                entities.append({
                    "id": str(tool.id),
                    "type": "tool",
                    "name": tool.name or f"Tool {str(tool.id)[:8]}",
                    "status": "active" if tool.is_active else "inactive",
                })
        
        result["entities"] = entities
    
    return result


@router.get("/{event_id}")
async def get_workflow_event(
    event_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific workflow event by ID"""
    event = db.query(WorkflowEvent).filter(WorkflowEvent.id == event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return event.to_dict()


class WorkflowControlRequest(BaseModel):
    """Request to control workflow execution"""
    action: str  # "pause", "resume", "cancel", "restart_from"


@router.post("/{workflow_id}/control")
async def control_workflow(
    workflow_id: str,
    request: WorkflowControlRequest,
    db: Session = Depends(get_db)
):
    """
    Control workflow execution
    
    Actions:
    - pause: Pause workflow execution
    - resume: Resume paused workflow
    - cancel: Cancel workflow execution
    - restart_from: Restart from a specific event (requires event_id in request)
    """
    # TODO: Implement workflow control logic
    # This would need integration with workflow execution engine
    return {
        "workflow_id": workflow_id,
        "action": request.action,
        "status": "acknowledged"
    }
