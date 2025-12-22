"""
API routes for workflow tracking - current execution process
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.database import get_db
from app.core.workflow_tracker import WorkflowStage, get_workflow_tracker
from app.models.task import Task, TaskStatus
from app.services.workflow_event_service import WorkflowEventService
from fastapi import APIRouter, Depends
from pydantic import BaseModel
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
    """Get current workflow execution process from WorkflowTracker and/or database"""
    tracker = get_workflow_tracker()
    event_service = WorkflowEventService(db)
    
    # PRIORITY 1: Get events from WorkflowTracker (real-time events from all sources)
    events_list = tracker.get_current_workflow()
    tracker_events = events_list if events_list is not None else []
    
    # PRIORITY 2: Load events from database for active workflows
    # Get active tasks to find their workflow_ids
    active_tasks = db.query(Task).filter(
        Task.status.in_([
            TaskStatus.PLANNING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.PENDING_APPROVAL,
            TaskStatus.EXECUTING,
            TaskStatus.PENDING
        ])
    ).order_by(Task.updated_at.desc()).limit(5).all()
    
    # Convert tracker events to response format (these are real-time and have priority)
    workflow_events = []
    tracker_event_timestamps = set()
    
    # Process WorkflowTracker events first (they are most current)
    for event in tracker_events:
        if isinstance(event, dict):
            workflow_events.append(WorkflowEventResponse(
                stage=event.get("stage", "execution"),
                message=event.get("message", ""),
                details=event.get("details", {}),
                timestamp=event.get("timestamp", datetime.now(timezone.utc).isoformat())
            ))
            tracker_event_timestamps.add(event.get("timestamp", ""))
    
    # PRIORITY 3: Load events from database for active tasks
    # Load events from DB for each active task (workflow_id = task_id)
    for task in active_tasks:
        task_workflow_id = str(task.id)
        try:
            db_events = event_service.get_events_by_workflow(task_workflow_id, limit=100)
            
            # Convert DB events to response format
            for db_event in db_events:
                event_timestamp = db_event.timestamp.isoformat() if db_event.timestamp else datetime.now(timezone.utc).isoformat()
                
                # Skip if already in tracker events (avoid duplicates)
                if event_timestamp not in tracker_event_timestamps:
                    # Merge event_data and event_metadata into details
                    details = {}
                    if db_event.event_data:
                        details.update(db_event.event_data)
                    if db_event.event_metadata:
                        details.update(db_event.event_metadata)
                    
                    workflow_events.append(WorkflowEventResponse(
                        stage=db_event.stage,
                        message=db_event.message,
                        details=details,
                        timestamp=event_timestamp
                    ))
                    tracker_event_timestamps.add(event_timestamp)
        except Exception as e:
            # Log but don't fail if DB events can't be loaded
            from app.core.logging_config import LoggingConfig
            logger = LoggingConfig.get_logger(__name__)
            logger.warning(f"Failed to load DB events for task {task.id}: {e}", exc_info=True)
    
    # PRIORITY 4: Also check for active tasks and their logs as supplement
    # (for backwards compatibility with old format)
    
    # PRIORITY 5: Supplement with task model_logs if no events found yet
    # (this helps when planning is done directly without WorkflowTracker integration)
    if not workflow_events and active_tasks:
        task = active_tasks[0]
        context = task.get_context()
        model_logs = context.get("model_logs", [])
        
        # Convert model logs to workflow events with better formatting
        for log in model_logs:
            if isinstance(log, dict):
                log_type = log.get("type", "")
                stage = log.get("stage", log.get("type", "execution"))
                content = log.get("content", {})
                metadata = log.get("metadata", {})
                
                # Extract readable information from content (which might be a dict)
                readable_content = ""
                if isinstance(content, dict):
                    # Extract meaningful information from content dict
                    if "prompt" in content:
                        readable_content = f"Запрос: {str(content['prompt'])[:100]}..."
                    elif "response" in content:
                        readable_content = f"Получен ответ ({content.get('full_length', 0)} символов)"
                    elif "analysis_type" in content:
                        readable_content = f"Анализ задачи: {content.get('analysis_type', '')}"
                    elif "result_type" in content:
                        readable_content = f"Результат: {content.get('result_type', '')}"
                    else:
                        readable_content = str(content)[:200]
                else:
                    readable_content = str(content)[:200]
                
                # Map log types to workflow stages and create readable messages
                if log_type == "request":
                    workflow_stage = WorkflowStage.EXECUTION.value
                    model = metadata.get("model", "")
                    server = metadata.get("server", "")
                    # Build concise message - model and server in message, no need for details
                    parts = ["Отправка запроса к модели"]
                    if model and model != "модель":
                        parts.append(model)
                    if server:
                        parts.append(f"({server})")
                    message = " ".join(parts) if len(parts) > 1 else parts[0]
                elif log_type == "response":
                    workflow_stage = WorkflowStage.EXECUTION.value
                    model = metadata.get("model", "")
                    duration = metadata.get("duration_ms", 0)
                    # Build concise message - duration in message, model/server can be in details if needed
                    parts = ["Получен ответ"]
                    if model and model != "модель":
                        parts.append(f"от {model}")
                    if duration:
                        parts.append(f"({duration/1000:.2f}с)")
                    message = " ".join(parts)
                elif log_type == "request_analysis":
                    workflow_stage = WorkflowStage.REQUEST_PARSING.value
                    # Extract meaningful info from readable_content
                    if isinstance(content, dict) and content.get("analysis_type") == "strategy_generation":
                        message = "Анализ задачи и создание стратегии"
                    else:
                        message = "Анализ запроса и определение действий"
                elif stage == "user_input" or stage == "user_request":
                    workflow_stage = WorkflowStage.USER_REQUEST.value
                    message = f"Поступил запрос от пользователя: {readable_content}"
                elif stage == "analysis" or stage == "request_analysis":
                    workflow_stage = WorkflowStage.REQUEST_PARSING.value
                    # Better formatting for analysis events
                    if isinstance(content, dict):
                        analysis_type = content.get("analysis_type", "")
                        if analysis_type == "strategy_generation":
                            message = "Создание стратегии решения задачи"
                        elif analysis_type:
                            message = f"Анализ: {analysis_type}"
                        else:
                            message = "Разбор запроса"
                    else:
                        message = readable_content or "Разбор запроса"
                elif stage == "action_progress":
                    workflow_stage = WorkflowStage.EXECUTION.value
                    message = readable_content or "Выполнение действий"
                elif stage == "result" or stage == "completion":
                    workflow_stage = WorkflowStage.RESULT.value
                    message = readable_content or "Результат"
                else:
                    workflow_stage = WorkflowStage.EXECUTION.value
                    message = readable_content or "Выполнение"
                
                log_timestamp = log.get("timestamp", datetime.now(timezone.utc).isoformat())
                
                # Only add if not already in tracker events (avoid duplicates)
                if log_timestamp not in tracker_event_timestamps:
                    # Clean up metadata - only keep fields not already in message
                    clean_metadata = {}
                    
                    # Don't add model/server/duration if already in message
                    if metadata.get("model") and "модель" not in message.lower() and metadata.get("model") != "модель":
                        clean_metadata["model"] = metadata["model"]
                    if metadata.get("server") and "server" not in message.lower():
                        clean_metadata["server"] = metadata["server"]
                    if metadata.get("duration_ms") and "с)" not in message and f"{metadata.get('duration_ms')/1000:.2f}" not in message:
                        clean_metadata["duration_ms"] = metadata["duration_ms"]
                    
                    # Always include steps_count, plan_id etc as they're usually not in message
                    if metadata.get("steps_count"):
                        clean_metadata["steps_count"] = metadata["steps_count"]
                    if metadata.get("plan_id"):
                        clean_metadata["plan_id"] = metadata["plan_id"]
                    
                    workflow_events.append(WorkflowEventResponse(
                        stage=workflow_stage,
                        message=message,
                        details=clean_metadata,
                        timestamp=log_timestamp
                    ))
    
    # Sort events by timestamp to ensure chronological order
    workflow_events.sort(key=lambda e: e.timestamp)
    
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
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get recent workflow events from database and WorkflowTracker"""
    event_service = WorkflowEventService(db)
    
    # Load from database (persistent events)
    db_events = event_service.get_recent_events(limit=limit)
    
    # Also get from WorkflowTracker (in-memory, real-time)
    tracker = get_workflow_tracker()
    tracker_events = tracker.get_all_recent_events(limit=limit)
    
    # Combine and deduplicate by timestamp
    all_events = []
    seen_timestamps = set()
    
    # Add DB events first (they are persistent)
    for db_event in db_events:
        event_timestamp = db_event.timestamp.isoformat() if db_event.timestamp else datetime.now(timezone.utc).isoformat()
        if event_timestamp not in seen_timestamps:
            details = {}
            if db_event.event_data:
                details.update(db_event.event_data)
            if db_event.event_metadata:
                details.update(db_event.event_metadata)
            
            all_events.append(WorkflowEventResponse(
                stage=db_event.stage,
                message=db_event.message,
                details=details,
                timestamp=event_timestamp
            ))
            seen_timestamps.add(event_timestamp)
    
    # Add tracker events (newest real-time events)
    for event in tracker_events:
        if isinstance(event, dict):
            event_timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())
            if event_timestamp not in seen_timestamps:
                all_events.append(WorkflowEventResponse(
                    stage=event.get("stage", "execution"),
                    message=event.get("message", ""),
                    details=event.get("details", {}),
                    timestamp=event_timestamp
                ))
                seen_timestamps.add(event_timestamp)
    
    # Sort by timestamp (newest first) and limit
    all_events.sort(key=lambda e: e.timestamp, reverse=True)
    return all_events[:limit]


@router.get("/workflow/{workflow_id}", response_model=List[WorkflowEventResponse])
async def get_workflow_events(
    workflow_id: str,
    limit: Optional[int] = None,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get all events for a specific workflow ID"""
    event_service = WorkflowEventService(db)
    db_events = event_service.get_events_by_workflow(workflow_id, limit=limit, offset=offset)
    
    # Convert to response format
    events = []
    for db_event in db_events:
        details = {}
        if db_event.event_data:
            details.update(db_event.event_data)
        if db_event.event_metadata:
            details.update(db_event.event_metadata)
        
        events.append(WorkflowEventResponse(
            stage=db_event.stage,
            message=db_event.message,
            details=details,
            timestamp=db_event.timestamp.isoformat() if db_event.timestamp else datetime.now(timezone.utc).isoformat()
        ))
    
    return events

