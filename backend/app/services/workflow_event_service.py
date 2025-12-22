"""
Service for managing workflow events in the database
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.logging_config import LoggingConfig
from app.core.workflow_tracker import WorkflowStage as TrackerStage
from app.models.workflow_event import (EventSource, EventStatus, EventType,
                                       WorkflowEvent, WorkflowStage)
from sqlalchemy import desc
from sqlalchemy.orm import Session

logger = LoggingConfig.get_logger(__name__)


class WorkflowEventService:
    """Service for persisting and retrieving workflow events"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def map_stage_to_canonical(self, stage: WorkflowStage) -> str:
        """
        Map internal WorkflowStage values to canonical stages required by contracts_v0:
          interpretation, validator_a, routing, planning, validator_b, execution, reflection
        Best-effort mapping; default to 'execution' when unknown.
        """
        try:
            s = stage.value.lower()
        except Exception:
            s = str(stage).lower()

        if s in ("user_request", "request_parsing"):
            return "interpretation"
        if s in ("action_determination", "decision_determination", "decision_routing"):
            return "routing"
        if s in ("execution",):
            return "execution"
        if s in ("result",):
            return "reflection"
        if s in ("error",):
            return "reflection"
        # fallback
        return "execution"

    def save_event(
        self,
        workflow_id: str,
        event_type: EventType,
        event_source: EventSource,
        stage: WorkflowStage,
        message: str,
        event_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        component_role: Optional[str] = None,
        prompt_id: Optional[UUID] = None,
        prompt_version: Optional[str] = None,
        decision_source: Optional[str] = None,
        task_id: Optional[UUID] = None,
        plan_id: Optional[UUID] = None,
        tool_id: Optional[UUID] = None,
        approval_request_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_event_id: Optional[UUID] = None,
        status: EventStatus = EventStatus.IN_PROGRESS,
        duration_ms: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> WorkflowEvent:
        """Save a workflow event to the database"""
        try:
            # Persist canonical stage name for compatibility with contracts_v0
            canonical_stage = self.map_stage_to_canonical(stage)
            event = WorkflowEvent(
                workflow_id=workflow_id,
                event_type=event_type.value,
                event_source=event_source.value,
                stage=canonical_stage,
                status=status.value,
                message=message,
                event_data=event_data or {},
                event_metadata=metadata or {},  # Use event_metadata instead of metadata
                component_role=component_role,
                prompt_id=prompt_id,
                prompt_version=prompt_version,
                decision_source=decision_source,
                task_id=task_id,
                plan_id=plan_id,
                tool_id=tool_id,
                approval_request_id=approval_request_id,
                session_id=session_id,
                trace_id=trace_id,
                parent_event_id=parent_event_id,
                duration_ms=duration_ms,
                timestamp=timestamp or datetime.now(timezone.utc)
            )
            
            self.db.add(event)
            self.db.commit()
            self.db.refresh(event)
            
            logger.debug(
                f"Saved workflow event: {event_type.value} - {message[:100]}",
                extra={
                    "workflow_id": workflow_id,
                    "event_type": event_type.value,
                    "stage": stage.value
                }
            )
            
            # Broadcast event via WebSocket (non-blocking)
            try:
                self._broadcast_event_async(event)
            except Exception as e:
                logger.warning(f"Failed to broadcast event via WebSocket: {e}", exc_info=True)
                # Don't fail the save if broadcast fails
            
            return event
        except Exception as e:
            self.db.rollback()
            logger.error(
                f"Failed to save workflow event: {e}",
                exc_info=True,
                extra={
                    "workflow_id": workflow_id,
                    "event_type": event_type.value,
                    "stage": stage.value
                }
            )
            raise
    
    def get_events_by_workflow(
        self,
        workflow_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[WorkflowEvent]:
        """Get all events for a workflow"""
        query = self.db.query(WorkflowEvent).filter(
            WorkflowEvent.workflow_id == workflow_id
        ).order_by(WorkflowEvent.timestamp.asc())
        
        if limit:
            query = query.limit(limit).offset(offset)
        
        return query.all()
    
    def get_recent_events(
        self,
        limit: int = 100,
        workflow_id: Optional[str] = None
    ) -> List[WorkflowEvent]:
        """Get recent events, optionally filtered by workflow_id"""
        query = self.db.query(WorkflowEvent)
        
        if workflow_id:
            query = query.filter(WorkflowEvent.workflow_id == workflow_id)
        
        return query.order_by(desc(WorkflowEvent.timestamp)).limit(limit).all()
    
    def update_event_status(
        self,
        event_id: UUID,
        status: EventStatus,
        duration_ms: Optional[int] = None,
        event_data: Optional[Dict[str, Any]] = None
    ) -> Optional[WorkflowEvent]:
        """Update event status and optionally add completion data"""
        event = self.db.query(WorkflowEvent).filter(WorkflowEvent.id == event_id).first()
        
        if not event:
            logger.warning(f"Event {event_id} not found for status update")
            return None
        
        event.status = status.value
        
        if duration_ms is not None:
            event.duration_ms = duration_ms
        
        if event_data:
            # Merge with existing event_data
            existing_data = event.event_data or {}
            existing_data.update(event_data)
            event.event_data = existing_data
        
        self.db.commit()
        self.db.refresh(event)
        
        return event
    
    def map_tracker_stage_to_workflow_stage(self, tracker_stage: TrackerStage) -> WorkflowStage:
        """Map WorkflowTracker stage to WorkflowEvent stage"""
        mapping = {
            TrackerStage.USER_REQUEST: WorkflowStage.USER_REQUEST,
            TrackerStage.REQUEST_PARSING: WorkflowStage.REQUEST_PARSING,
            TrackerStage.ACTION_DETERMINATION: WorkflowStage.ACTION_DETERMINATION,
            TrackerStage.EXECUTION: WorkflowStage.EXECUTION,
            TrackerStage.RESULT: WorkflowStage.RESULT,
            TrackerStage.ERROR: WorkflowStage.ERROR,
        }
        return mapping.get(tracker_stage, WorkflowStage.EXECUTION)
    
    def _broadcast_event_async(self, event: WorkflowEvent):
        """Broadcast event via WebSocket asynchronously (non-blocking)"""
        try:
            # Import broadcast function and connection manager
            from app.api.routes.websocket_events import manager

            # Convert event to dict for broadcasting
            event_dict = event.to_dict()
            
            message = {
                "type": "event",
                "data": event_dict
            }
            
            # Use threading to broadcast without blocking
            import asyncio
            import threading
            
            def run_broadcast():
                """Run broadcast in a new event loop"""
                try:
                    # Create new event loop for this thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    
                    try:
                        # Broadcast to workflow-specific connections
                        workflow_id = event.workflow_id
                        new_loop.run_until_complete(
                            manager.broadcast_to_workflow(message, workflow_id)
                        )
                        
                        # Also broadcast to "all workflows" connections
                        new_loop.run_until_complete(
                            manager.broadcast_to_all(message)
                        )
                    finally:
                        new_loop.close()
                except Exception as e:
                    logger.debug(f"Error in broadcast thread: {e}")
            
            # Start broadcast in background thread (non-blocking)
            thread = threading.Thread(target=run_broadcast, daemon=True)
            thread.start()
                
        except Exception as e:
            # Fail silently to not break the save operation
            logger.debug(f"Could not broadcast event: {e}")

