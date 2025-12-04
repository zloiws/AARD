"""
API routes for workflow tracking - current execution process
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from datetime import datetime

from app.core.workflow_tracker import get_workflow_tracker, WorkflowStage
from app.core.database import get_db
from app.models.task import Task, TaskStatus
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/workflow", tags=["workflow"])


class WorkflowEventResponse(BaseModel):
    """Workflow event response"""
    stage: str
    message: str
    details: Dict[str, Any] = {}
    timestamp: str


class WorkflowResponse(BaseModel):
    """Current workflow response"""
    is_active: bool
    events: List[WorkflowEventResponse] = []
    current_stage: Optional[str] = None


@router.get("/current", response_model=WorkflowResponse)
async def get_current_workflow(
    db: Session = Depends(get_db)
):
    """Get current workflow execution process"""
    tracker = get_workflow_tracker()
    
    # Get events from tracker
    events_list = tracker.get_current_workflow()
    events = events_list if events_list is not None else []
    
    # Also check for active tasks and their logs
    active_tasks = db.query(Task).filter(
        Task.status.in_([
            TaskStatus.PLANNING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.PENDING_APPROVAL,
            TaskStatus.EXECUTING
        ])
    ).order_by(Task.updated_at.desc()).limit(1).all()
    
    # Merge with task logs if available (always check even if events exist)
    if active_tasks:
        task = active_tasks[0]
        context = task.get_context()
        model_logs = context.get("model_logs", [])
        
        # Convert model logs to workflow events
        events = []
        for log in model_logs:
            if isinstance(log, dict):
                stage = log.get("stage", log.get("type", "execution"))
                content = log.get("content", "")
                
                # Map stages
                if stage == "user_input" or stage == "user_request":
                    workflow_stage = WorkflowStage.USER_REQUEST.value
                    message = f"Поступил запрос от пользователя: {str(content)[:200]}"
                elif stage == "analysis" or stage == "request_analysis":
                    workflow_stage = WorkflowStage.REQUEST_PARSING.value
                    message = f"Разбор запроса: {str(content)[:200]}"
                elif stage == "action_progress":
                    workflow_stage = WorkflowStage.EXECUTION.value
                    message = f"Выполнение действий: {str(content)[:200]}"
                elif stage == "result" or stage == "completion":
                    workflow_stage = WorkflowStage.RESULT.value
                    message = f"Результат: {str(content)[:200]}"
                else:
                    workflow_stage = WorkflowStage.EXECUTION.value
                    message = f"{str(content)[:200]}"
                
                events.append(WorkflowEventResponse(
                    stage=workflow_stage,
                    message=message,
                    details=log.get("metadata", {}),
                    timestamp=log.get("timestamp", datetime.utcnow().isoformat())
                ))
    
    if not events:
        events = []
    
    # Convert to response format first
    workflow_events = []
    for event in events:
        if isinstance(event, dict):
            workflow_events.append(WorkflowEventResponse(**event))
        elif hasattr(event, 'stage'):
            # It's already a WorkflowEventResponse
            workflow_events.append(event)
        else:
            # Try to convert from dict-like object
            try:
                workflow_events.append(WorkflowEventResponse(
                    stage=event.get("stage", "execution"),
                    message=event.get("message", ""),
                    details=event.get("details", {}),
                    timestamp=event.get("timestamp", datetime.utcnow().isoformat())
                ))
            except Exception:
                pass
    
    # Determine current stage
    current_stage = None
    is_active = False
    
    if workflow_events:
        # Get last event's stage
        last_event = workflow_events[-1]
        current_stage = last_event.stage if hasattr(last_event, 'stage') else str(last_event.get("stage", ""))
        
        is_active = current_stage not in [WorkflowStage.RESULT.value, WorkflowStage.ERROR.value, "completed", "error"]
    
    return WorkflowResponse(
        is_active=is_active,
        events=workflow_events,
        current_stage=current_stage
    )


@router.get("/recent", response_model=List[WorkflowEventResponse])
async def get_recent_workflow_events(
    limit: int = 50
):
    """Get recent workflow events"""
    tracker = get_workflow_tracker()
    events = tracker.get_all_recent_events(limit=limit)
    
    return [WorkflowEventResponse(**event) for event in events]

