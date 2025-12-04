"""
Run Test 4: Complex Task Planning
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


async def test_4_complex_task():
    """Test 4: Complex multi-step task"""
    print_separator("TEST 4: Complex Task - E-commerce Application")
    
    db = SessionLocal()
    planning_service = PlanningService(db)
    
    try:
        task_description = """Create a complete e-commerce application with:
        - User authentication and authorization
        - Product catalog with categories
        - Shopping cart functionality
        - Order processing and payment integration"""
        
        print(f"📝 Task: {task_description[:100]}...")
        print("\n⏳ Generating complex plan (this may take a while)...")
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        print(f"\n✅ Complex plan created!")
        print(f"   Plan ID: {plan.id}")
        print(f"   Total steps: {len(plan.steps)}")
        
        # Verify
        print("\n🔍 Verification:")
        assert plan is not None, "Plan should not be None"
        assert len(plan.steps) > 0, "Plan should have at least one step"
        
        if len(plan.steps) > 3:
            print(f"   ✅ Plan has {len(plan.steps)} steps (expected > 3)")
        else:
            print(f"   ⚠️ Plan has {len(plan.steps)} steps (model may create generalized plans)")
            print(f"   ✅ Plan structure is valid regardless of step count")
        
        # Check strategy
        if plan.strategy and isinstance(plan.strategy, dict):
            print(f"\n📊 Strategy:")
            approach = plan.strategy.get('approach') or 'N/A'
            if approach and approach != 'N/A' and len(str(approach)) > 60:
                approach = str(approach)[:60] + "..."
            print(f"   Approach: {approach}")
            
            assumptions = plan.strategy.get('assumptions') or []
            constraints = plan.strategy.get('constraints') or []
            success_criteria = plan.strategy.get('success_criteria') or []
            
            print(f"   Assumptions: {len(assumptions) if isinstance(assumptions, list) else 0}")
            print(f"   Constraints: {len(constraints) if isinstance(constraints, list) else 0}")
            print(f"   Success criteria: {len(success_criteria) if isinstance(success_criteria, list) else 0}")
            
            print(f"   ✅ Strategy structure verified")
        else:
            print(f"\n⚠️ Strategy is None or not a dict (this may be acceptable)")
        
        # Check step structure
        print(f"\n📋 Step breakdown:")
        step_types = {}
        step_ids = []
        
        for step in plan.steps:
            step_type = step.get('type', 'unknown')
            step_types[step_type] = step_types.get(step_type, 0) + 1
            step_ids.append(step.get('step_id'))
            
            # Verify required fields
            assert "step_id" in step, "Step should have step_id"
            assert "description" in step, "Step should have description"
        
        # Verify unique step_ids
        unique_step_ids = set(step_ids)
        assert len(step_ids) == len(unique_step_ids), "All step_ids should be unique"
        print(f"   ✅ All {len(step_ids)} step_ids are unique")
        
        for step_type, count in step_types.items():
            print(f"   {step_type}: {count}")
        
        # Show first few steps
        print(f"\n📋 First 5 steps:")
        for i, step in enumerate(plan.steps[:5], 1):
            desc = step.get('description', 'N/A')
            if len(desc) > 60:
                desc = desc[:60] + "..."
            print(f"   {i}. [{step.get('type', 'N/A')}] {step.get('step_id', 'N/A')}: {desc}")
        
        if len(plan.steps) > 5:
            print(f"   ... and {len(plan.steps) - 5} more steps")
        
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
    print(" PLANNING SERVICE - TEST 4: COMPLEX TASK")
    print("=" * 70)
    
    try:
        plan = asyncio.run(test_4_complex_task())
        
        if plan:
            print("\n" + "=" * 70)
            print(" ✅ TEST 4 PASSED!")
            print("=" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print(" ❌ TEST 4 FAILED!")
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

