"""
Run Test 5: Error Recovery - Replanning After Failure
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime

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


async def test_5_error_recovery():
    """Test 5: Replanning after errors"""
    print_separator("TEST 5: Error Recovery - Replanning After Failure")
    
    db = SessionLocal()
    planning_service = PlanningService(db)
    
    try:
        task_description = "Create a data processing pipeline"
        
        print(f"📝 Task: {task_description}")
        print("\n⏳ Step 1: Creating initial plan...")
        
        plan1 = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        print(f"✅ Initial plan created (version {plan1.version}, {len(plan1.steps)} steps)")
        
        # Simulate errors in Digital Twin context
        task = db.query(Task).filter(Task.id == plan1.task_id).first()
        
        execution_logs = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "error",
                "message": "Step 2 failed: Missing pandas dependency",
                "step_id": "step_2",
                "error": "ModuleNotFoundError: No module named 'pandas'"
            },
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "warning",
                "message": "Step 3 skipped due to dependency failure",
                "step_id": "step_3"
            }
        ]
        
        task.update_context({
            "execution_logs": execution_logs
        }, merge=True)
        
        task.add_to_history("error_feedback", {
            "errors": ["Missing pandas dependency"],
            "suggestions": ["Add dependency installation step"]
        })
        db.commit()
        
        print(f"✅ Simulated {len(execution_logs)} execution errors logged in Digital Twin")
        print(f"   Errors:")
        for log in execution_logs:
            print(f"   - [{log['level']}] {log['message']}")
        
        # Replan with error context
        print("\n⏳ Step 2: Replanning with error context...")
        
        plan2 = await planning_service.replan(
            plan_id=plan1.id,
            reason="Previous execution failed due to missing dependencies",
            context={
                "execution_errors": execution_logs,
                "feedback": "Need to add dependency installation"
            }
        )
        
        print(f"\n✅ Replanning completed!")
        print(f"   Plan 1 version: {plan1.version}")
        print(f"   Plan 2 version: {plan2.version}")
        print(f"   Plan 2 steps: {len(plan2.steps)}")
        
        # Verify
        print("\n🔍 Verification:")
        assert plan2 is not None, "Plan 2 should not be None"
        assert plan2.version > plan1.version, "Plan 2 version should be higher"
        print(f"   ✅ Plan 2 version is higher ({plan2.version} > {plan1.version})")
        
        # Check if new plan addresses the error (soft check)
        step_descriptions = " ".join([
            step.get("description", "").lower() for step in plan2.steps
        ])
        
        error_keywords = ["dependenc", "install", "requirement", "pip", "package", "library", "module"]
        has_fix = any(keyword in step_descriptions for keyword in error_keywords)
        
        print(f"\n🔍 Error addressed in new plan:")
        if has_fix:
            print(f"   ✅ Yes - new plan mentions dependency/keywords")
            print(f"   Found keywords: {[kw for kw in error_keywords if kw in step_descriptions]}")
        else:
            print(f"   ⚠️ Not clearly visible in step descriptions")
            print(f"   (Model may have addressed it differently)")
        
        # Check execution logs are still in context
        db.refresh(task)
        context = task.get_context()
        context_logs = context.get('execution_logs', [])
        
        print(f"\n📋 Execution logs in context: {len(context_logs)}")
        if len(context_logs) > 0:
            print(f"   ✅ Execution logs preserved in Digital Twin")
        
        # Show interaction history
        history = context.get('interaction_history', [])
        print(f"\n📋 Interaction history: {len(history)} entries")
        if history:
            for i, entry in enumerate(history[-2:], 1):
                print(f"   {i}. [{entry.get('type', 'N/A')}] {entry.get('timestamp', 'N/A')[:19]}")
        
        return plan1, plan2
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        db.close()


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print(" PLANNING SERVICE - TEST 5: ERROR RECOVERY")
    print("=" * 70)
    
    try:
        plan1, plan2 = asyncio.run(test_5_error_recovery())
        
        if plan1 and plan2:
            print("\n" + "=" * 70)
            print(" ✅ TEST 5 PASSED!")
            print("=" * 70 + "\n")
        else:
            print("\n" + "=" * 70)
            print(" ❌ TEST 5 FAILED!")
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

