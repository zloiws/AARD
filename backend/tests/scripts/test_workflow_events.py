"""
Test script for workflow events persistence
"""
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.workflow_event import (EventSource, EventStatus, EventType,
                                       WorkflowStage)
from app.services.workflow_event_service import WorkflowEventService
from sqlalchemy.orm import Session


def test_workflow_events():
    """Test saving and loading workflow events"""
    print("=" * 80)
    print("TEST: Workflow Events Persistence")
    print("=" * 80)
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        event_service = WorkflowEventService(db)
        workflow_id = f"test_{uuid.uuid4()}"
        
        print(f"\n1. Creating test workflow: {workflow_id}")
        
        # Test 1: Save user input event
        print("\n2. Saving USER_INPUT event...")
        event1 = event_service.save_event(
            workflow_id=workflow_id,
            event_type=EventType.USER_INPUT,
            event_source=EventSource.USER,
            stage=WorkflowStage.USER_REQUEST,
            message="Тестовый запрос пользователя",
            event_data={"user_message": "Привет, как дела?"},
            metadata={"username": "test_user", "session_id": "test_session"}
        )
        print(f"   ✅ Event saved: {event1.id}")
        
        # Test 2: Save model request event
        print("\n3. Saving MODEL_REQUEST event...")
        event2 = event_service.save_event(
            workflow_id=workflow_id,
            event_type=EventType.MODEL_REQUEST,
            event_source=EventSource.MODEL,
            stage=WorkflowStage.EXECUTION,
            message="Отправка запроса к модели",
            event_data={
                "prompt": "System: You are a helpful assistant\nUser: Привет",
                "system_prompt": "You are a helpful assistant",
                "user_prompt": "Привет"
            },
            metadata={
                "model": "gemma3:4b",
                "server": "Server 2 - Coding",
                "temperature": 0.7
            },
            trace_id="test_trace_123",
            parent_event_id=event1.id
        )
        print(f"   ✅ Event saved: {event2.id}")
        
        # Test 3: Save model response event
        print("\n4. Saving MODEL_RESPONSE event...")
        event3 = event_service.save_event(
            workflow_id=workflow_id,
            event_type=EventType.MODEL_RESPONSE,
            event_source=EventSource.MODEL,
            stage=WorkflowStage.EXECUTION,
            message="Получен ответ от модели",
            event_data={
                "response": "Привет! Как дела? Чем могу помочь?",
                "response_length": 32
            },
            metadata={
                "model": "gemma3:4b",
                "duration_ms": 1500
            },
            trace_id="test_trace_123",
            parent_event_id=event2.id,
            duration_ms=1500,
            status=EventStatus.COMPLETED
        )
        print(f"   ✅ Event saved: {event3.id}")
        
        # Test 4: Load events by workflow
        print(f"\n5. Loading all events for workflow: {workflow_id}")
        events = event_service.get_events_by_workflow(workflow_id)
        print(f"   ✅ Loaded {len(events)} events")
        
        for i, event in enumerate(events, 1):
            print(f"\n   Event {i}:")
            print(f"      Type: {event.event_type}")
            print(f"      Source: {event.event_source}")
            print(f"      Stage: {event.stage}")
            print(f"      Message: {event.message[:80]}...")
            print(f"      Timestamp: {event.timestamp}")
            if event.event_metadata:
                print(f"      Metadata keys: {list(event.event_metadata.keys())}")
        
        # Test 5: Load recent events
        print(f"\n6. Loading recent events...")
        recent_events = event_service.get_recent_events(limit=5)
        print(f"   ✅ Loaded {len(recent_events)} recent events")
        
        # Test 6: Verify data integrity
        print(f"\n7. Verifying data integrity...")
        assert len(events) == 3, f"Expected 3 events, got {len(events)}"
        assert events[0].event_type == EventType.USER_INPUT.value
        assert events[1].event_type == EventType.MODEL_REQUEST.value
        assert events[2].event_type == EventType.MODEL_RESPONSE.value
        assert events[1].parent_event_id == event1.id
        assert events[2].parent_event_id == event2.id
        print("   ✅ All assertions passed!")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_workflow_events()

