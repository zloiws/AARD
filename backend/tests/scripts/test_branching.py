"""
Test branching visualization endpoints and functionality
"""
import sys
import asyncio
from pathlib import Path
from uuid import uuid4

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.models.plan import Plan
from app.services.planning_service import PlanningService
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def print_separator(title: str):
    """Print test separator"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


async def test_branching_visualization():
    """Test branching visualization functionality"""
    print_separator("TEST: Branching Visualization")
    
    db = SessionLocal()
    planning_service = PlanningService(db)
    
    try:
        # Test 1: Create a task and plan
        print("📝 Test 1: Creating task and plan...")
        task_description = "Test branching visualization - simple task"
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        task = db.query(Task).filter(Task.id == plan.task_id).first()
        print(f"✅ Task created: {task.id}")
        print(f"✅ Plan created: {plan.id} (version {plan.version})")
        
        # Check context
        context = task.get_context()
        print(f"\n📋 Context keys: {list(context.keys())}")
        
        # Check if branching data is in context
        if "planning_decisions" in context:
            print("✅ Planning decisions found in context")
            planning_decisions = context["planning_decisions"]
            print(f"   - Alternatives: {len(planning_decisions.get('alternatives', []))}")
            print(f"   - Replanning history: {len(planning_decisions.get('replanning_history', []))}")
        else:
            print("⚠️ Planning decisions not found in context")
        
        if "agent_selection" in context:
            print("✅ Agent selection found in context")
        else:
            print("⚠️ Agent selection not found in context")
        
        if "prompt_usage" in context:
            print("✅ Prompt usage found in context")
        else:
            print("⚠️ Prompt usage not found in context")
        
        if "tool_selection" in context:
            print("✅ Tool selection found in context")
        else:
            print("⚠️ Tool selection not found in context")
        
        if "memory_storage" in context:
            print("✅ Memory storage found in context")
        else:
            print("⚠️ Memory storage not found in context")
        
        # Test 2: Replanning
        print("\n📝 Test 2: Testing replanning...")
        
        new_plan = await planning_service.replan(
            plan_id=plan.id,
            reason="Test replanning to check history",
            context={"test": True}
        )
        
        print(f"✅ Replanning completed: new plan version {new_plan.version}")
        
        # Check replanning history - need to refresh task
        db.refresh(task)
        context = task.get_context()
        
        if "planning_decisions" in context:
            replanning_history = context["planning_decisions"].get("replanning_history", [])
            print(f"✅ Replanning history: {len(replanning_history)} entries")
            if replanning_history:
                last_entry = replanning_history[-1]
                print(f"   - From version {last_entry.get('from_version')} to {last_entry.get('to_version')}")
                print(f"   - Reason: {last_entry.get('reason')}")
            else:
                print("   ⚠️ Replanning history is empty - checking if context was preserved...")
                print(f"   - Context has planning_decisions: {context.get('planning_decisions', {})}")
        
        # Test 3: Check summary endpoint data structure
        print("\n📝 Test 3: Checking summary data structure...")
        
        # Manually check what summary would contain
        plans = db.query(Plan).filter(Plan.task_id == task.id).order_by(Plan.version).all()
        print(f"✅ Total plans for task: {len(plans)}")
        for p in plans:
            print(f"   - Plan v{p.version}: {p.status} ({len(p.steps) if p.steps else 0} steps)")
        
        # Test 4: Check active tasks
        print("\n📝 Test 4: Checking active tasks...")
        
        # Update task status to make it active
        task.status = TaskStatus.IN_PROGRESS
        db.commit()
        
        active_tasks = db.query(Task).filter(
            Task.status.in_([
                TaskStatus.PLANNING,
                TaskStatus.IN_PROGRESS,
                TaskStatus.PENDING_APPROVAL,
                TaskStatus.EXECUTING,
                TaskStatus.PAUSED
            ])
        ).all()
        
        print(f"✅ Active tasks found: {len(active_tasks)}")
        for t in active_tasks:
            print(f"   - Task {str(t.id)[:8]}...: {t.status} - {t.description[:50]}")
        
        print("\n" + "=" * 70)
        print(" ✅ All tests completed successfully!")
        print("=" * 70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = asyncio.run(test_branching_visualization())
    sys.exit(0 if success else 1)

