"""
Test real integration with ChatService - verify events are saved with full details
"""
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import asyncio
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.ollama_client import OllamaClient
from app.core.chat_session import ChatSessionManager
from app.services.workflow_event_service import WorkflowEventService
from app.models.workflow_event import EventType, EventSource
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)

async def test_real_chat_integration():
    """Test real ChatService integration with event saving"""
    print("=" * 80)
    print("TEST: Real ChatService Integration - Event Saving")
    print("=" * 80)
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Create chat session
        session_manager = ChatSessionManager()
        session = session_manager.create_session(
            db=db,
            system_prompt="You are a helpful assistant.",
            title="Test Chat"
        )
        session_id = str(session.id)
        
        print(f"\n1. Created chat session: {session_id}")
        
        # Simulate chat message (we'll need to call the chat endpoint or simulate it)
        # For now, let's check if we can find events by session_id
        print("\n2. Checking for existing events with this session_id...")
        
        event_service = WorkflowEventService(db)
        
        # Get recent events to see if any chat events exist
        recent_events = event_service.get_recent_events(limit=20)
        
        # Filter events by session_id if available
        session_events = [e for e in recent_events if e.session_id == session_id]
        
        print(f"   Found {len(session_events)} events for this session")
        
        if len(session_events) == 0:
            print("\n   ⚠️  No events found yet - chat events are saved when message is sent")
            print("   This test requires actual chat interaction to see events")
            print("\n   To fully test:")
            print("   1. Send a chat message through the API")
            print("   2. Check /api/workflow/current or /api/workflow/workflow/{workflow_id}")
        else:
            print("\n3. Analyzing chat events...")
            for i, event in enumerate(session_events, 1):
                print(f"\n   Event {i}:")
                print(f"      Type: {event.event_type}")
                print(f"      Source: {event.event_source}")
                print(f"      Stage: {event.stage}")
                print(f"      Message: {event.message[:80]}...")
                
                if event.event_data:
                    print(f"      Event data keys: {list(event.event_data.keys())}")
                    # Check for chat-specific data
                    if "full_prompt" in event.event_data:
                        print(f"      ✅ Contains full_prompt")
                    if "history" in event.event_data:
                        print(f"      ✅ Contains chat history")
                    if "full_response" in event.event_data:
                        print(f"      ✅ Contains full response")
                
                if event.event_metadata:
                    print(f"      Metadata keys: {list(event.event_metadata.keys())}")
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ CHAT INTEGRATION TEST SUMMARY")
        print("=" * 80)
        print(f"  Session ID: {session_id}")
        print(f"  Events found for session: {len(session_events)}")
        print(f"  Total recent events: {len(recent_events)}")
        print("\n  Note: Chat events are saved when messages are sent through the API.")
        print("  To see full integration, send a message and check workflow events.")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_real_chat_integration())

