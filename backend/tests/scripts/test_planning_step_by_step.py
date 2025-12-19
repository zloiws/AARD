"""
Step-by-step planning tests - run one at a time, from simple to complex
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal
from app.core.logging_config import LoggingConfig
from app.models.task import Task
from app.services.planning_service import PlanningService

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
            print(f"   {i}. {step.get('step_id', 'N/A')}: {step.get('description', 'N/A')[:60]}...")
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
        print(f"   Original request: {context.get('original_user_request', 'N/A')[:60]}...")
        print(f"   Active todos: {len(context.get('active_todos', []))}")
        print(f"   Plan ID in context: {context.get('plan', {}).get('plan_id', 'N/A')}")
        
        # Show active todos
        if context.get('active_todos'):
            print("\n📋 Active ToDos:")
            for i, todo in enumerate(context['active_todos'][:3], 1):
                print(f"   {i}. {todo.get('description', 'N/A')[:50]}...")
        
        return task, context
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        db.close()


async def test_3_with_artifacts():
    """Test 3: Planning with existing artifacts in context"""
    print_separator("TEST 3: Planning with Existing Artifacts")
    
    db = SessionLocal()
    planning_service = PlanningService(db)
    
    try:
        # First, create a task
        task_description = "Create a REST API endpoint for user management"
        
        print(f"📝 Task: {task_description}")
        print("\n⏳ Step 1: Creating initial plan...")
        
        plan1 = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        # Add artifacts to context
        task = db.query(Task).filter(Task.id == plan1.task_id).first()
        task.update_context({
            "artifacts": [
                {
                    "artifact_id": "test-artifact-1",
                    "type": "code",
                    "name": "database.py",
                    "description": "Database connection module"
                },
                {
                    "artifact_id": "test-artifact-2",
                    "type": "code",
                    "name": "models.py",
                    "description": "User models"
                }
            ]
        }, merge=True)
        db.commit()
        
        print(f"✅ Added 2 artifacts to context")
        
        # Replan with context
        print("\n⏳ Step 2: Replanning with artifacts in context...")
        
        plan2 = await planning_service.replan(
            plan_id=plan1.id,
            reason="Need to integrate with existing database module",
            context={"artifacts_available": True}
        )
        
        print(f"\n✅ Replanning completed!")
        print(f"   Plan 1 version: {plan1.version}")
        print(f"   Plan 2 version: {plan2.version}")
        print(f"   Plan 2 steps: {len(plan2.steps)}")
        
        # Check context preserved artifacts
        task.refresh()
        context = task.get_context()
        print(f"\n📦 Artifacts in context: {len(context.get('artifacts', []))}")
        
        return plan1, plan2
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        db.close()


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
        
        if isinstance(plan.strategy, dict):
            print(f"   Strategy approach: {plan.strategy.get('approach', 'N/A')[:60]}...")
            print(f"   Assumptions: {len(plan.strategy.get('assumptions', []))}")
            print(f"   Constraints: {len(plan.strategy.get('constraints', []))}")
        
        print("\n📋 Step breakdown:")
        step_types = {}
        for step in plan.steps:
            step_type = step.get('type', 'unknown')
            step_types[step_type] = step_types.get(step_type, 0) + 1
        
        for step_type, count in step_types.items():
            print(f"   {step_type}: {count}")
        
        return plan
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()


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
        
        # Simulate errors
        task = db.query(Task).filter(Task.id == plan1.task_id).first()
        task.update_context({
            "execution_logs": [
                {
                    "timestamp": "2025-12-03T20:00:00",
                    "level": "error",
                    "message": "Step 2 failed: Missing pandas dependency",
                    "step_id": "step_2"
                }
            ]
        }, merge=True)
        
        task.add_to_history("error_feedback", {
            "errors": ["Missing pandas dependency"],
            "suggestions": ["Add dependency installation step"]
        })
        db.commit()
        
        print(f"✅ Simulated execution error logged")
        
        print("\n⏳ Step 2: Replanning with error context...")
        
        plan2 = await planning_service.replan(
            plan_id=plan1.id,
            reason="Previous execution failed due to missing dependencies",
            context={
                "execution_errors": task.get_context().get("execution_logs", []),
                "feedback": "Need to add dependency installation"
            }
        )
        
        print(f"\n✅ Replanning completed!")
        print(f"   Plan 1 version: {plan1.version}")
        print(f"   Plan 2 version: {plan2.version}")
        print(f"   Plan 2 steps: {len(plan2.steps)}")
        
        # Check if new plan addresses the error
        step_descriptions = " ".join([
            step.get("description", "").lower() for step in plan2.steps
        ])
        
        has_fix = any(keyword in step_descriptions for keyword in 
                     ["dependenc", "install", "requirement", "pip", "package"])
        
        print(f"\n🔍 Error addressed: {'✅ Yes' if has_fix else '⚠️ Not clearly visible'}")
        
        return plan1, plan2
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        db.close()


def main():
    """Run tests step by step"""
    print("\n" + "=" * 70)
    print(" PLANNING SERVICE TESTS - STEP BY STEP")
    print("=" * 70)
    print("\nTests will run in sequence, from simple to complex.")
    print("You can interrupt and run individual tests if needed.\n")
    
    tests = [
        ("Test 1: Simple Task", test_1_simple_task),
        ("Test 2: Digital Twin Context", test_2_check_digital_twin),
        ("Test 3: With Artifacts", test_3_with_artifacts),
        ("Test 4: Complex Task", test_4_complex_task),
        ("Test 5: Error Recovery", test_5_error_recovery),
    ]
    
    print("Available tests:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    
    print("\nEnter test number (1-5) or 'all' to run all tests:")
    choice = input("> ").strip().lower()
    
    if choice == "all":
        # Run all tests
        for name, test_func in tests:
            try:
                asyncio.run(test_func())
                print("\n✅ Press Enter to continue to next test...")
                input()
            except KeyboardInterrupt:
                print("\n\n⚠️ Tests interrupted by user")
                break
    elif choice.isdigit() and 1 <= int(choice) <= len(tests):
        # Run single test
        idx = int(choice) - 1
        name, test_func = tests[idx]
        asyncio.run(test_func())
    else:
        print("Invalid choice. Please run the script again.")


if __name__ == "__main__":
    main()

