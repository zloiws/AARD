"""
WebSocket API for real-time workflow events
"""
import asyncio
import json
from typing import Set, Dict, Optional
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.workflow_event_service import WorkflowEventService
from app.models.workflow_event import WorkflowEvent
from app.core.logging_config import LoggingConfig

router = APIRouter(prefix="/api/ws", tags=["websocket"])
logger = LoggingConfig.get_logger(__name__)

# Store active WebSocket connections
class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Map workflow_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map WebSocket -> workflow_id
        self.websocket_to_workflow: Dict[WebSocket, str] = {}
        # All connections (for broadcast)
        self.all_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, workflow_id: Optional[str] = None):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.all_connections.add(websocket)
        
        if workflow_id:
            if workflow_id not in self.active_connections:
                self.active_connections[workflow_id] = set()
            self.active_connections[workflow_id].add(websocket)
            self.websocket_to_workflow[websocket] = workflow_id
            logger.info(f"WebSocket connected for workflow: {workflow_id}")
        else:
            logger.info("WebSocket connected (all workflows)")
    
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.all_connections.discard(websocket)
        
        workflow_id = self.websocket_to_workflow.pop(websocket, None)
        if workflow_id and workflow_id in self.active_connections:
            self.active_connections[workflow_id].discard(websocket)
            if not self.active_connections[workflow_id]:
                del self.active_connections[workflow_id]
        
        logger.info(f"WebSocket disconnected (workflow: {workflow_id or 'all'})")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_workflow(self, message: dict, workflow_id: str):
        """Broadcast message to all connections for a specific workflow"""
        if workflow_id not in self.active_connections:
            return
        
        disconnected = []
        for websocket in self.active_connections[workflow_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for websocket in self.all_connections.copy():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to broadcast to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)

# Global connection manager
manager = ConnectionManager()


async def poll_and_send_events(
    websocket: WebSocket,
    workflow_id: Optional[str],
    db: Session,
    last_timestamp: Optional[datetime] = None
):
    """Poll database for new events and send via WebSocket"""
    event_service = WorkflowEventService(db)
    
    try:
        while True:
            # Get new events since last timestamp
            if workflow_id:
                events = event_service.get_events_by_workflow(workflow_id, limit=100)
            else:
                events = event_service.get_recent_events(limit=100)
            
            # Filter events after last_timestamp
            if last_timestamp:
                new_events = [
                    e for e in events
                    if e.timestamp and e.timestamp > last_timestamp
                ]
            else:
                new_events = events[:10]  # Send last 10 events on first connection
            
            if new_events:
                for event in new_events:
                    # Convert to dict
                    event_dict = event.to_dict()
                    
                    # Send event
                    await manager.send_personal_message({
                        "type": "event",
                        "data": event_dict
                    }, websocket)
                    
                    # Update last timestamp
                    if event.timestamp:
                        last_timestamp = event.timestamp
                
                logger.debug(f"Sent {len(new_events)} events via WebSocket")
            
            # Wait before next poll
            await asyncio.sleep(0.5)  # Poll every 500ms for real-time updates
            
    except asyncio.CancelledError:
        logger.info("Event polling cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in event polling: {e}", exc_info=True)
        await manager.send_personal_message({
            "type": "error",
            "message": str(e)
        }, websocket)


@router.websocket("/events")
async def websocket_events(websocket: WebSocket, workflow_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time workflow events
    
    Query parameters:
    - workflow_id: Optional workflow ID to subscribe to specific workflow events
    """
    await manager.connect(websocket, workflow_id)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connected",
            "workflow_id": workflow_id,
            "message": "Connected to workflow events stream"
        }, websocket)
        
        # Get database session
        db = next(get_db())
        
        try:
            # Start polling for new events
            await poll_and_send_events(websocket, workflow_id, db)
        finally:
            db.close()
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.websocket("/events/{workflow_id}")
async def websocket_events_for_workflow(websocket: WebSocket, workflow_id: str):
    """
    WebSocket endpoint for specific workflow events
    """
    await websocket_events(websocket, workflow_id=workflow_id)


# Helper function to broadcast new event to connected clients
async def broadcast_new_event(event: WorkflowEvent):
    """Broadcast new event to all subscribed WebSocket connections"""
    try:
        event_dict = event.to_dict()
        
        message = {
            "type": "event",
            "data": event_dict
        }
        
        # Broadcast to workflow-specific connections
        workflow_id = event.workflow_id
        await manager.broadcast_to_workflow(message, workflow_id)
        
        # Also broadcast to "all workflows" connections
        await manager.broadcast_to_all(message)
        
        logger.debug(f"Broadcasted event {event.id} to WebSocket clients")
    except Exception as e:
        logger.warning(f"Failed to broadcast event: {e}", exc_info=True)

