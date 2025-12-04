"""
Run Test 2: Digital Twin Context Check
"""
import sys
import asyncio
from pathlib import Path
import json

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.task import Task
from app.services.planning_service import PlanningService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def print_separator(title: str):
    """Print test separator"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


async def test_2_check_digital_twin():
    """Test 2: Check Digital Twin context"""
    print_separator("TEST 2: Digital Twin Context Check")
    
    db = SessionLocal()
    planning_service = PlanningService(db)
    
    try:
        task_description = "Write a function to calculate factorial of a number"
        
        print(f"📝 Task: {task_description}")
        print("\n⏳ Generating plan and checking Digital Twin...")
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        # Get task and context
        task = db.query(Task).filter(Task.id == plan.task_id).first()
        context = task.get_context()
        
        print(f"\n✅ Digital Twin context verified!")
        print(f"   Task ID: {task.id}")
        print(f"   Context keys: {list(context.keys())}")
        
        # Verify required fields
        print("\n🔍 Verification:")
        
        # Check original_user_request
        assert "original_user_request" in context, "Context should have original_user_request"
        assert context["original_user_request"] == task_description, "Original request should match"
        print(f"   ✅ original_user_request: {context['original_user_request'][:50]}...")
        
        # Check active_todos
        assert "active_todos" in context, "Context should have active_todos"
        assert isinstance(context["active_todos"], list), "active_todos should be a list"
        assert len(context["active_todos"]) > 0, "active_todos should not be empty"
        print(f"   ✅ active_todos: {len(context['active_todos'])} items")
        
        # Check plan
        assert "plan" in context, "Context should have plan"
        assert context["plan"]["plan_id"] == str(plan.id), "Plan ID should match"
        assert context["plan"]["version"] == plan.version, "Plan version should match"
        print(f"   ✅ plan: ID={context['plan']['plan_id'][:8]}..., version={context['plan']['version']}")
        
        # Check other required fields
        required_fields = ["artifacts", "execution_logs", "interaction_history", "metadata"]
        for field in required_fields:
            assert field in context, f"Context should have {field}"
            print(f"   ✅ {field}: present")
        
        # Show active todos
        if context.get('active_todos'):
            print("\n📋 Active ToDos:")
            for i, todo in enumerate(context['active_todos'][:3], 1):
                desc = todo.get('description', 'N/A')
                if len(desc) > 50:
                    desc = desc[:50] + "..."
                print(f"   {i}. {todo.get('step_id', 'N/A')}: {desc}")
        
        # Show metadata
        if context.get('metadata'):
            print("\n📊 Metadata:")
            metadata = context['metadata']
            print(f"   Task ID: {metadata.get('task_id', 'N/A')[:8]}...")
            print(f"   Plan ID: {metadata.get('plan_id', 'N/A')[:8]}...")
            print(f"   Created: {metadata.get('created_at', 'N/A')}")
        
        return task, context
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" PLANNING SERVICE - TEST 2: DIGITAL TWIN CONTEXT")
    print("=" * 70)
    
    try:
        task, context = asyncio.run(test_2_check_digital_twin())
        
        if task and context:
            print("\n" + "=" * 70)
            print(" ✅ TEST 2 PASSED!")
            print("=" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print(" ❌ TEST 2 FAILED!")
            print("=" * 70 + "\n")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

