"""
Test real integration with PlanningService - verify events are saved with full details
"""
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import asyncio
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.planning_service import PlanningService
from app.services.workflow_event_service import WorkflowEventService
from app.models.workflow_event import EventType, EventSource
from app.models.task import Task, TaskStatus
from uuid import UUID

async def test_real_planning_integration():
    """Test real PlanningService integration with event saving"""
    print("=" * 80)
    print("TEST: Real PlanningService Integration - Event Saving")
    print("=" * 80)
    
    # Get database session
    db: Session = next(get_db())
    
    try:
        # Create PlanningService instance
        planning_service = PlanningService(db)
        
        print("\n1. Creating a test task...")
        task_description = "Create a simple Python script that prints 'Hello, World!'"
        
        # Generate plan (this should trigger event saving)
        print("\n2. Generating plan (this will save events to DB)...")
        plan = await planning_service.generate_plan(
            task_description=task_description,
            task_id=None,  # Will be created automatically
            context=None
        )
        
        print(f"   ✅ Plan created: ID={plan.id}, Steps={len(plan.steps) if plan.steps else 0}")
        
        # Get the task that was created
        task = db.query(Task).filter(Task.plan_id == plan.id).first()
        if not task:
            # Try to find task by description
            task = db.query(Task).filter(Task.description == task_description).order_by(Task.created_at.desc()).first()
        
        assert task is not None, "Task should be created"
        print(f"   ✅ Task found: ID={task.id}, Status={task.status}")
        
        # Get workflow_id (should be task.id as string)
        workflow_id = str(task.id)
        
        # Load events from database
        print(f"\n3. Loading workflow events for workflow: {workflow_id}")
        event_service = WorkflowEventService(db)
        events = event_service.get_events_by_workflow(workflow_id)
        
        print(f"   ✅ Loaded {len(events)} events from database")
        
        # Verify events exist
        assert len(events) > 0, "Should have at least one event saved"
        
        # Show all event types
        print(f"\n4. All event types found:")
        event_types = {}
        for event in events:
            event_type = event.event_type
            if event_type not in event_types:
                event_types[event_type] = []
            event_types[event_type].append(event)
        
        for event_type, type_events in event_types.items():
            print(f"   - {event_type}: {len(type_events)} event(s)")
        
        # Check for MODEL_REQUEST events with full prompts
        model_request_events = [
            e for e in events 
            if e.event_type == EventType.MODEL_REQUEST.value
        ]
        
        print(f"\n5. Checking MODEL_REQUEST events ({len(model_request_events)} found)...")
        
        if len(model_request_events) > 0:
            for i, event in enumerate(model_request_events, 1):
                print(f"\n   Event {i}:")
                print(f"      Type: {event.event_type}")
                print(f"      Source: {event.event_source}")
                print(f"      Message: {event.message[:80]}...")
                
                # Verify event_data contains full prompts
                assert event.event_data is not None, f"Event {i} should have event_data"
                event_data = event.event_data
                
                # Check for prompt fields
                has_system = "system_prompt" in event_data
                has_user = "user_prompt" in event_data
                has_full = "full_prompt" in event_data
                
                print(f"      Has system_prompt: {has_system}")
                print(f"      Has user_prompt: {has_user}")
                print(f"      Has full_prompt: {has_full}")
                
                if has_system:
                    system_len = len(str(event_data["system_prompt"]))
                    print(f"      system_prompt length: {system_len} chars")
                    assert system_len > 0, "system_prompt should not be empty"
                
                if has_user:
                    user_len = len(str(event_data["user_prompt"]))
                    print(f"      user_prompt length: {user_len} chars")
                    assert user_len > 0, "user_prompt should not be empty"
                
                if has_full:
                    full_len = len(str(event_data["full_prompt"]))
                    print(f"      full_prompt length: {full_len} chars")
                    assert full_len > 50, "full_prompt should be substantial"
                
                print(f"   ✅ Event {i} has required prompt fields")
        else:
            print("   ⚠️  No MODEL_REQUEST events found - events might be saved differently")
        
        # Check for MODEL_RESPONSE events with full responses
        model_response_events = [
            e for e in events 
            if e.event_type == EventType.MODEL_RESPONSE.value
        ]
        
        print(f"\n6. Checking MODEL_RESPONSE events ({len(model_response_events)} found)...")
        
        if len(model_response_events) > 0:
            for i, event in enumerate(model_response_events, 1):
                print(f"\n   Event {i}:")
                print(f"      Type: {event.event_type}")
                print(f"      Source: {event.event_source}")
                print(f"      Message: {event.message[:80]}...")
                print(f"      Duration: {event.duration_ms}ms")
                
                # Verify event_data contains full response
                assert event.event_data is not None, f"Event {i} should have event_data"
                event_data = event.event_data
                
                has_full_response = "full_response" in event_data
                has_response_length = "response_length" in event_data
                
                print(f"      Has full_response: {has_full_response}")
                print(f"      Has response_length: {has_response_length}")
                
                if has_full_response:
                    response_len = len(str(event_data["full_response"]))
                    print(f"      full_response length: {response_len} chars")
                    assert response_len > 0, "full_response should not be empty"
                    
                    # Show preview
                    preview = str(event_data["full_response"])[:100]
                    print(f"      Response preview: {preview}...")
                
                if has_response_length:
                    print(f"      response_length: {event_data['response_length']} chars")
                
                print(f"   ✅ Event {i} has required response fields")
        else:
            print("   ⚠️  No MODEL_RESPONSE events found")
        
        # Check for completion event
        completion_events = [
            e for e in events 
            if e.event_type == EventType.COMPLETION.value
        ]
        
        print(f"\n7. Checking COMPLETION events ({len(completion_events)} found)...")
        
        # Show detailed info for all events
        print(f"\n8. Detailed event information:")
        for i, event in enumerate(events, 1):
            print(f"\n   Event {i}:")
            print(f"      Type: {event.event_type}")
            print(f"      Source: {event.event_source}")
            print(f"      Stage: {event.stage}")
            print(f"      Message: {event.message[:80]}...")
            if event.event_data:
                print(f"      Event data keys: {list(event.event_data.keys())}")
                # Check for prompts/response
                if "system_prompt" in event.event_data or "user_prompt" in event.event_data or "full_prompt" in event.event_data:
                    print(f"      ✅ Contains prompts")
                if "full_response" in event.event_data:
                    print(f"      ✅ Contains full response")
            if event.event_metadata:
                print(f"      Metadata keys: {list(event.event_metadata.keys())}")
            if event.duration_ms:
                print(f"      Duration: {event.duration_ms}ms")
        if len(completion_events) > 0:
            for event in completion_events:
                print(f"   ✅ Completion event found: {event.message[:80]}...")
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ REAL INTEGRATION TEST SUMMARY")
        print("=" * 80)
        print(f"  Total events saved: {len(events)}")
        print(f"  MODEL_REQUEST events: {len(model_request_events)}")
        print(f"  MODEL_RESPONSE events: {len(model_response_events)}")
        print(f"  COMPLETION events: {len(completion_events)}")
        print(f"  Task ID: {task.id}")
        print(f"  Plan ID: {plan.id}")
        
        # Verify we have at least some events with full details
        events_with_details = 0
        for event in events:
            if event.event_data and len(event.event_data) > 0:
                events_with_details += 1
        
        print(f"\n  Events with detailed data: {events_with_details}/{len(events)}")
        
        if events_with_details > 0:
            print("\n✅ TEST PASSED - Events are being saved with full details!")
        else:
            print("\n⚠️  WARNING - No events have detailed data yet")
        
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_real_planning_integration())

