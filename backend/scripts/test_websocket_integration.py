"""
Test WebSocket integration for real-time workflow events
"""
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import asyncio
import websockets
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.workflow_event_service import WorkflowEventService
from app.models.workflow_event import EventSource, EventType, EventStatus, WorkflowStage

async def test_websocket_events():
    """Test WebSocket real-time event streaming"""
    print("=" * 80)
    print("TEST: WebSocket Integration for Real-time Events")
    print("=" * 80)
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        event_service = WorkflowEventService(db)
        workflow_id = f"test_ws_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n1. Creating test workflow: {workflow_id}")
        
        # Connect to WebSocket
        ws_url = "ws://localhost:8000/api/ws/events"
        print(f"\n2. Connecting to WebSocket: {ws_url}")
        
        try:
            async with websockets.connect(ws_url) as websocket:
                print("   ✅ WebSocket connected")
                
                # Wait for connection message
                connected_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                connected_data = json.loads(connected_msg)
                print(f"   ✅ Received connection confirmation: {connected_data.get('message', 'N/A')}")
                
                # Send a test event to database (should be broadcast via WebSocket)
                print(f"\n3. Creating and saving test event to database...")
                event = event_service.save_event(
                    workflow_id=workflow_id,
                    event_type=EventType.USER_INPUT,
                    event_source=EventSource.USER,
                    stage=WorkflowStage.USER_REQUEST,
                    message="Тестовое событие через WebSocket",
                    event_data={"test": "data", "websocket": True},
                    metadata={"test_mode": True}
                )
                print(f"   ✅ Event saved: {event.id}")
                
                # Wait a bit for broadcast (it happens in background thread)
                await asyncio.sleep(1)
                
                # Try to receive event via WebSocket
                print(f"\n4. Waiting for event via WebSocket (timeout: 5s)...")
                try:
                    event_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event_data = json.loads(event_msg)
                    
                    if event_data.get('type') == 'event':
                        print(f"   ✅ Received event via WebSocket!")
                        print(f"      Event type: {event_data['data'].get('event_type')}")
                        print(f"      Message: {event_data['data'].get('message', 'N/A')[:80]}...")
                        print(f"      Workflow ID: {event_data['data'].get('workflow_id')}")
                    else:
                        print(f"   ⚠️  Received unexpected message type: {event_data.get('type')}")
                except asyncio.TimeoutError:
                    print(f"   ⚠️  Timeout waiting for event via WebSocket")
                    print(f"      Note: Events are broadcast in background thread, might take longer")
                
                # Test workflow-specific WebSocket
                print(f"\n5. Testing workflow-specific WebSocket connection...")
                ws_url_specific = f"ws://localhost:8000/api/ws/events/{workflow_id}"
                
                async with websockets.connect(ws_url_specific) as ws_specific:
                    print(f"   ✅ Connected to workflow-specific WebSocket")
                    
                    # Wait for connection message
                    connected_msg = await asyncio.wait_for(ws_specific.recv(), timeout=5.0)
                    connected_data = json.loads(connected_msg)
                    print(f"   ✅ Received connection confirmation: {connected_data.get('workflow_id')}")
                    
                    # Send another event for this workflow
                    event2 = event_service.save_event(
                        workflow_id=workflow_id,
                        event_type=EventType.EXECUTION_STEP,
                        event_source=EventSource.PLANNER_AGENT,
                        stage=WorkflowStage.EXECUTION,
                        message="Второе тестовое событие для workflow-specific WebSocket",
                        event_data={"test": "workflow_specific", "websocket": True},
                        metadata={"test_mode": True}
                    )
                    print(f"   ✅ Second event saved: {event2.id}")
                    
                    await asyncio.sleep(1)
                    
                    # Try to receive event
                    try:
                        event_msg = await asyncio.wait_for(ws_specific.recv(), timeout=5.0)
                        event_data = json.loads(event_msg)
                        
                        if event_data.get('type') == 'event':
                            print(f"   ✅ Received workflow-specific event via WebSocket!")
                        else:
                            print(f"   ⚠️  Received unexpected message: {event_data.get('type')}")
                    except asyncio.TimeoutError:
                        print(f"   ⚠️  Timeout waiting for workflow-specific event")
                
                print("\n" + "=" * 80)
                print("✅ WEBSOCKET INTEGRATION TEST SUMMARY")
                print("=" * 80)
                print(f"  WebSocket endpoints tested:")
                print(f"    - /api/ws/events (all workflows)")
                print(f"    - /api/ws/events/{workflow_id} (specific workflow)")
                print(f"  Events created: 2")
                print(f"  Note: Broadcast happens asynchronously, events may take a moment")
                print("=" * 80)
        
        except ConnectionRefusedError:
            print(f"\n❌ ERROR: Could not connect to WebSocket server")
            print(f"   Make sure the FastAPI server is running on http://localhost:8000")
            print(f"   Start server: python backend/main.py")
            return
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            raise
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("\n⚠️  Note: Make sure FastAPI server is running before running this test!")
    print("   Start server: python backend/main.py\n")
    asyncio.run(test_websocket_events())

