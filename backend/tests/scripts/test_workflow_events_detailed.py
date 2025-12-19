"""
Test script for detailed workflow events (full prompts, responses)
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


def test_detailed_workflow_events():
    """Test saving and loading detailed workflow events with full prompts"""
    print("=" * 80)
    print("TEST: Detailed Workflow Events (Full Prompts & Responses)")
    print("=" * 80)
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        event_service = WorkflowEventService(db)
        workflow_id = f"test_detailed_{uuid.uuid4()}"
        
        print(f"\n1. Creating test workflow: {workflow_id}")
        
        # Test 1: Save MODEL_REQUEST event with full prompts
        print("\n2. Saving MODEL_REQUEST event with full prompts...")
        system_prompt = "You are a helpful AI assistant that analyzes tasks and creates strategic plans."
        user_prompt = "Create a simple Python script that prints 'Hello, World!'"
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        context = {"task_id": "123", "priority": 5}
        
        event1 = event_service.save_event(
            workflow_id=workflow_id,
            event_type=EventType.MODEL_REQUEST,
            event_source=EventSource.PLANNER_AGENT,
            stage=WorkflowStage.EXECUTION,
            message="Отправка запроса к модели для анализа задачи",
            event_data={
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "full_prompt": full_prompt,
                "task_type": "analyze_task",
                "context_used": True,
                "context": context
            },
            metadata={
                "model": "gemma3:4b",
                "server": "Server 2 - Coding",
                "server_url": "http://10.39.0.6:11434/v1"
            },
            trace_id="test_trace_detailed_123"
        )
        print(f"   ✅ Event saved: {event1.id}")
        
        # Verify event_data contains full prompts
        assert event1.event_data is not None, "event_data should not be None"
        assert "system_prompt" in event1.event_data, "system_prompt should be in event_data"
        assert "user_prompt" in event1.event_data, "user_prompt should be in event_data"
        assert "full_prompt" in event1.event_data, "full_prompt should be in event_data"
        assert event1.event_data["system_prompt"] == system_prompt, "system_prompt should match"
        assert event1.event_data["user_prompt"] == user_prompt, "user_prompt should match"
        assert event1.event_data["full_prompt"] == full_prompt, "full_prompt should match"
        print("   ✅ All prompts verified in event_data")
        
        # Test 2: Save MODEL_RESPONSE event with full response
        print("\n3. Saving MODEL_RESPONSE event with full response...")
        full_response = """{
  "approach": "This task involves a straightforward implementation of a basic Python script. The approach will be to use the print() function to output the specified string.",
  "complexity": "low",
  "estimated_time": "5 minutes",
  "requirements": ["Python 3.x"]
}"""
        
        event2 = event_service.save_event(
            workflow_id=workflow_id,
            event_type=EventType.MODEL_RESPONSE,
            event_source=EventSource.PLANNER_AGENT,
            stage=WorkflowStage.EXECUTION,
            message="Получен ответ от модели",
            event_data={
                "full_response": full_response,
                "response_length": len(full_response),
                "task_type": "analyze_task"
            },
            metadata={
                "model": "gemma3:4b",
                "duration_ms": 6505
            },
            trace_id="test_trace_detailed_123",
            parent_event_id=event1.id,
            duration_ms=6505,
            status=EventStatus.COMPLETED
        )
        print(f"   ✅ Event saved: {event2.id}")
        
        # Verify full response is saved
        assert event2.event_data is not None, "event_data should not be None"
        assert "full_response" in event2.event_data, "full_response should be in event_data"
        assert event2.event_data["full_response"] == full_response, "full_response should match"
        assert event2.event_data["response_length"] == len(full_response), "response_length should match"
        print("   ✅ Full response verified in event_data")
        
        # Test 3: Save chat event with history
        print("\n4. Saving chat MODEL_REQUEST with history...")
        chat_history = [
            {"role": "user", "content": "Привет"},
            {"role": "assistant", "content": "Привет! Как дела?"}
        ]
        chat_system_prompt = "You are a helpful assistant."
        chat_user_prompt = "Как дела?"
        chat_full_prompt = f"{chat_system_prompt}\n\nUser: {chat_user_prompt}\nAssistant:"
        
        event3 = event_service.save_event(
            workflow_id=workflow_id,
            event_type=EventType.MODEL_REQUEST,
            event_source=EventSource.MODEL,
            stage=WorkflowStage.EXECUTION,
            message="Отправка запроса к модели для чата",
            event_data={
                "system_prompt": chat_system_prompt,
                "user_prompt": chat_user_prompt,
                "full_prompt": chat_full_prompt,
                "task_type": "general_chat",
                "temperature": 0.7,
                "history_length": len(chat_history),
                "history": chat_history
            },
            metadata={
                "model": "gemma3:4b",
                "server": "Server 2 - Coding"
            },
            session_id="test_session_123",
            trace_id="test_trace_chat_456"
        )
        print(f"   ✅ Event saved: {event3.id}")
        
        # Verify chat history is saved
        assert event3.event_data is not None, "event_data should not be None"
        assert "history" in event3.event_data, "history should be in event_data"
        assert len(event3.event_data["history"]) == len(chat_history), "history length should match"
        assert event3.event_data["history"][0]["role"] == "user", "first history item should be user"
        print("   ✅ Chat history verified in event_data")
        
        # Test 4: Load events and verify all details
        print(f"\n5. Loading all events for workflow: {workflow_id}")
        events = event_service.get_events_by_workflow(workflow_id)
        print(f"   ✅ Loaded {len(events)} events")
        
        # Verify all events have detailed data
        assert len(events) == 3, f"Expected 3 events, got {len(events)}"
        
        # Check first event (MODEL_REQUEST for planning)
        event1_loaded = [e for e in events if e.event_type == EventType.MODEL_REQUEST.value and e.event_source == EventSource.PLANNER_AGENT.value][0]
        assert event1_loaded.event_data is not None, "Event 1 should have event_data"
        assert "full_prompt" in event1_loaded.event_data, "Event 1 should have full_prompt"
        assert len(event1_loaded.event_data["full_prompt"]) > 100, "Event 1 full_prompt should be substantial"
        print("   ✅ Event 1 (planning request) has full prompts")
        
        # Check second event (MODEL_RESPONSE)
        event2_loaded = [e for e in events if e.event_type == EventType.MODEL_RESPONSE.value][0]
        assert event2_loaded.event_data is not None, "Event 2 should have event_data"
        assert "full_response" in event2_loaded.event_data, "Event 2 should have full_response"
        assert len(event2_loaded.event_data["full_response"]) > 100, "Event 2 full_response should be substantial"
        print("   ✅ Event 2 (model response) has full response")
        
        # Check third event (chat request)
        event3_loaded = [e for e in events if e.event_type == EventType.MODEL_REQUEST.value and e.event_source == EventSource.MODEL.value][0]
        assert event3_loaded.event_data is not None, "Event 3 should have event_data"
        assert "history" in event3_loaded.event_data, "Event 3 should have history"
        assert len(event3_loaded.event_data["history"]) == 2, "Event 3 should have 2 history items"
        print("   ✅ Event 3 (chat request) has history")
        
        # Test 5: Verify to_dict() includes all data
        print("\n6. Verifying to_dict() method includes all details...")
        event_dict = event2_loaded.to_dict()
        assert "event_data" in event_dict, "to_dict should include event_data"
        assert "metadata" in event_dict, "to_dict should include metadata"
        assert "full_response" in event_dict["event_data"], "to_dict event_data should include full_response"
        print("   ✅ to_dict() includes all details")
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS PASSED!")
        print("=" * 80)
        print("\nSummary:")
        print(f"  - Saved {len(events)} events with detailed information")
        print(f"  - All events contain full prompts/responses in event_data")
        print(f"  - Chat events include conversation history")
        print(f"  - All data is retrievable and verifiable")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_detailed_workflow_events()

