"""
Run Test 1: Simple Task Planning
"""
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.services.planning_service import PlanningService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def print_separator(title: str):
    """Print test separator"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


async def test_1_simple_task():
    """Test 1: Create a simple task and plan"""
    print_separator("TEST 1: Simple Task - Print 'Hello, World!'")
    
    db = SessionLocal()
    planning_service = PlanningService(db)
    
    try:
        task_description = "Create a simple Python script that prints 'Hello, World!'"
        
        print(f"📝 Task: {task_description}")
        print("\n⏳ Generating plan...")
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        print(f"\n✅ Plan created successfully!")
        print(f"   Plan ID: {plan.id}")
        print(f"   Status: {plan.status}")
        print(f"   Version: {plan.version}")
        print(f"   Steps: {len(plan.steps)}")
        
        print("\n📋 Steps:")
        for i, step in enumerate(plan.steps[:5], 1):  # Show first 5 steps
            step_desc = step.get('description', 'N/A')
            if len(step_desc) > 60:
                step_desc = step_desc[:60] + "..."
            print(f"   {i}. {step.get('step_id', 'N/A')}: {step_desc}")
        if len(plan.steps) > 5:
            print(f"   ... and {len(plan.steps) - 5} more steps")
        
        # Verify plan structure
        print("\n🔍 Verification:")
        assert plan is not None, "Plan should not be None"
        assert plan.goal == task_description, "Plan goal should match task description"
        assert len(plan.steps) > 0, "Plan should have at least one step"
        
        for step in plan.steps:
            assert "step_id" in step, "Step should have step_id"
            assert "description" in step, "Step should have description"
            assert "type" in step, "Step should have type"
        
        print("   ✅ Plan structure verified")
        print("   ✅ All steps have required fields")
        
        return plan
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" PLANNING SERVICE - TEST 1: SIMPLE TASK")
    print("=" * 70)
    
    try:
        plan = asyncio.run(test_1_simple_task())
        
        if plan:
            print("\n" + "=" * 70)
            print(" ✅ TEST 1 PASSED!")
            print("=" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print(" ❌ TEST 1 FAILED!")
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

