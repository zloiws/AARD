"""
WebSocket API for real-time workflow events
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Optional, Set

from app.core.database import get_session_local
from app.core.logging_config import LoggingConfig
from app.models.workflow_event import WorkflowEvent
from app.services.workflow_event_service import WorkflowEventService
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

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
        # Accept WebSocket connection (CORS handled by FastAPI middleware)
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
            # Check if websocket is still connected
            if websocket.client_state.name in ('DISCONNECTED', 'CLOSED'):
                self.disconnect(websocket)
                return

            # Additional check for connection validity
            try:
                _ = websocket.client
            except (AttributeError, RuntimeError):
                logger.debug("WebSocket connection invalid, disconnecting")
                self.disconnect(websocket)
                return

            await websocket.send_json(message)
        except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
            # Connection already closed or disconnected
            logger.debug(f"WebSocket connection closed: {e}")
            self.disconnect(websocket)
        except Exception as e:
            # Other errors - log but don't spam
            error_str = str(e)
            # 1001 = going away (normal client disconnect)
            # 1005 = no status received (connection closed without status)
            # 1006 = abnormal closure
            if any(code in error_str for code in ['1001', '1005', 'going away', 'no status received']):
                logger.debug(f"WebSocket connection closed by client: {e}")
            else:
                logger.warning(f"Failed to send message to WebSocket: {e}")
            self.disconnect(websocket)
    
    async def broadcast_to_workflow(self, message: dict, workflow_id: str):
        """Broadcast message to all connections for a specific workflow"""
        if workflow_id not in self.active_connections:
            return
        
        disconnected = []
        for websocket in list(self.active_connections[workflow_id]):  # Copy to avoid modification during iteration
            try:
                # Check if websocket is still connected
                if websocket.client_state.name in ('DISCONNECTED', 'CLOSED'):
                    disconnected.append(websocket)
                    continue
                
                await websocket.send_json(message)
            except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
                # Connection already closed
                logger.debug(f"WebSocket connection closed during broadcast: {e}")
                disconnected.append(websocket)
            except Exception as e:
                # Other errors - log but don't spam
                error_str = str(e)
                # 1001 = going away (normal client disconnect)
                # 1005 = no status received (connection closed without status)
                if any(code in error_str for code in ['1001', '1005', 'going away', 'no status received']):
                    logger.debug(f"WebSocket connection closed by client during workflow broadcast: {e}")
                else:
                    logger.warning(f"Failed to broadcast to WebSocket: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket)
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        for websocket in list(self.all_connections):  # Copy to avoid modification during iteration
            try:
                # Check if websocket is still connected
                if websocket.client_state.name in ('DISCONNECTED', 'CLOSED'):
                    disconnected.append(websocket)
                    continue
                
                await websocket.send_json(message)
            except (WebSocketDisconnect, ConnectionError, RuntimeError) as e:
                # Connection already closed
                logger.debug(f"WebSocket connection closed during broadcast: {e}")
                disconnected.append(websocket)
            except Exception as e:
                # Other errors - log but don't spam
                error_str = str(e)
                # 1001 = going away (normal client disconnect)
                # 1005 = no status received (connection closed without status)
                if any(code in error_str for code in ['1001', '1005', 'going away', 'no status received']):
                    logger.debug(f"WebSocket connection closed by client during all broadcast: {e}")
                else:
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
    last_timestamp: Optional[datetime] = None
):
    """Poll database for new events and send via WebSocket
    
    Creates a new database session for each poll to avoid connection pool exhaustion.
    """
    from app.core.database import get_session_local
    
    SessionLocal = get_session_local()
    
    try:
        while True:
            # Check if websocket is still connected before polling
            if websocket.client_state.name in ('DISCONNECTED', 'CLOSED'):
                logger.debug("WebSocket disconnected, stopping event polling")
                break

            # Additional check - try to access websocket properties to detect closure
            try:
                _ = websocket.client
            except (AttributeError, RuntimeError):
                logger.debug("WebSocket connection invalid, stopping event polling")
                break
            
            # Create a new session for each poll to avoid holding connections
            db = SessionLocal()
            try:
                event_service = WorkflowEventService(db)
                
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
                
                # Convert events to dicts while session is still open
                event_dicts = []
                for event in new_events:
                    event_dicts.append(event.to_dict())
                    # Update last timestamp
                    if event.timestamp:
                        last_timestamp = event.timestamp
                
            finally:
                # Always close the session immediately after use
                db.close()
            
            # Send events after closing the session
            if event_dicts:
                # Check if websocket is still connected before sending
                if websocket.client_state.name in ('DISCONNECTED', 'CLOSED'):
                    logger.debug("WebSocket disconnected, stopping event polling")
                    break
                
                for event_dict in event_dicts:
                    # Check connection before each message
                    if websocket.client_state.name in ('DISCONNECTED', 'CLOSED'):
                        break
                    
                    # Send event
                    await manager.send_personal_message({
                        "type": "event",
                        "data": event_dict
                    }, websocket)
                
                logger.debug(f"Sent {len(event_dicts)} events via WebSocket")
            
            # Wait before next poll
            try:
                await asyncio.sleep(0.5)  # Poll every 500ms for real-time updates
            except asyncio.CancelledError:
                # Cancelled during sleep - normal shutdown
                logger.debug("Event polling sleep cancelled")
                raise
            
    except asyncio.CancelledError:
        # Normal cancellation during shutdown or disconnect
        logger.debug("Event polling cancelled")
        raise
    except WebSocketDisconnect:
        logger.debug("WebSocket disconnected during event polling")
        raise
    except Exception as e:
        logger.error(f"Error in event polling: {e}", exc_info=True)
        # Try to send error message, but don't fail if connection is closed
        try:
            if websocket.client_state.name not in ('DISCONNECTED', 'CLOSED'):
                await manager.send_personal_message({
                    "type": "error",
                    "message": str(e)
                }, websocket)
        except (asyncio.CancelledError, WebSocketDisconnect):
            # Normal cancellation or disconnect, ignore
            pass
        except Exception:
            # Connection already closed or other error, ignore
            pass


@router.websocket("/events")
async def websocket_events(websocket: WebSocket, workflow_id: Optional[str] = None):
    """
    WebSocket endpoint for real-time workflow events

    Query parameters:
    - workflow_id: Optional workflow ID to subscribe to specific workflow events
    """
    logger.info(f"WebSocket connection attempt from {websocket.client.host}:{websocket.client.port}, workflow_id: {workflow_id}")

    await manager.connect(websocket, workflow_id)
    logger.info(f"WebSocket connection established for workflow_id: {workflow_id}")

    try:
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connected",
            "workflow_id": workflow_id,
            "message": "Connected to workflow events stream"
        }, websocket)
        
        # Start polling for new events (creates its own sessions)
        polling_task = asyncio.create_task(poll_and_send_events(websocket, workflow_id))
        try:
            await polling_task
        except asyncio.CancelledError:
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
            
    except asyncio.CancelledError:
        # Normal cancellation during shutdown
        logger.debug("WebSocket cancelled")
        manager.disconnect(websocket)
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

#
# Additional WebSocket endpoints for chat/execution/meta channels
#


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for chat events for a specific session.
    Clients should connect to receive chat-related updates.
    """
    workflow_key = f"chat:{session_id}"
    logger.info(f"WebSocket chat connect: session_id={session_id}, from={websocket.client.host}:{websocket.client.port}")
    await manager.connect(websocket, workflow_key)
    try:
        # Keep connection open; client may send pings or commands
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket chat disconnected: session_id={session_id}")
    except Exception as e:
        logger.error(f"WebSocket chat error: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.websocket("/ws/execution/{session_id}")
async def websocket_execution_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for execution graph events for a specific session.
    """
    workflow_key = f"execution:{session_id}"
    logger.info(f"WebSocket execution connect: session_id={session_id}, from={websocket.client.host}:{websocket.client.port}")
    await manager.connect(websocket, workflow_key)
    try:
        while True:
            await websocket.receive_text()  # client only listens
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket execution disconnected: session_id={session_id}")
    except Exception as e:
        logger.error(f"WebSocket execution error: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.websocket("/ws/meta")
async def websocket_meta_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for meta-events (system evolution).
    """
    workflow_key = "meta:global"
    logger.info(f"WebSocket meta connect from {websocket.client.host}:{websocket.client.port}")
    await manager.connect(websocket, workflow_key)
    try:
        while True:
            await websocket.receive_text()  # client only listens
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket meta disconnected")
    except Exception as e:
        logger.error(f"WebSocket meta error: {e}", exc_info=True)
        manager.disconnect(websocket)


# Helper broadcasters for external services
async def broadcast_chat_event(session_id: str, event: Dict):
    """Broadcast chat event to chat subscribers for a session."""
    try:
        message = {"type": "chat_event", "session_id": session_id, "data": event}
        await manager.broadcast_to_workflow(message, f"chat:{session_id}")
        # Also broadcast to all connected clients so global monitors receive chat events
        await manager.broadcast_to_all(message)
    except Exception:
        logger.debug("Failed to broadcast chat event", exc_info=True)


async def broadcast_execution_event(session_id: str, event: Dict):
    """Broadcast execution event to execution subscribers for a session."""
    try:
        message = {"type": "execution_event", "session_id": session_id, "data": event}
        await manager.broadcast_to_workflow(message, f"execution:{session_id}")
        # Also broadcast to all connected clients so global monitors receive execution events
        await manager.broadcast_to_all(message)
    except Exception:
        logger.debug("Failed to broadcast execution event", exc_info=True)


async def broadcast_meta_event(event: Dict):
    """Broadcast meta event to meta subscribers (and all as fallback)."""
    try:
        message = {"type": "meta_event", "data": event}
        await manager.broadcast_to_workflow(message, "meta:global")
        # Also broadcast to all connected clients
        await manager.broadcast_to_all(message)
    except Exception:
        logger.debug("Failed to broadcast meta event", exc_info=True)

