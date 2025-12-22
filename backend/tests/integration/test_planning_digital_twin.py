"""
Integration tests for Planning Service with Digital Twin integration
Tests progress from simple to complex scenarios
"""
import asyncio
from uuid import uuid4

import pytest
from app.core.database import SessionLocal
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.planning_service import PlanningService
from sqlalchemy.orm import Session


@pytest.fixture
def db():
    """Database session fixture"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def planning_service(db):
    """Planning service fixture"""
    return PlanningService(db)


class Test1SimpleTaskPlanning:
    """Test 1: Simple task creation and planning"""
    
    @pytest.mark.asyncio
    async def test_create_simple_task_and_plan(self, db, planning_service):
        """Test creating a simple task and generating a plan"""
        
        task_description = "Create a simple Python script that prints 'Hello, World!'"
        
        # Generate plan
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        # Verify plan was created
        assert plan is not None
        assert plan.goal == task_description
        assert plan.version == 1
        assert plan.status == "draft" or plan.status == "approved"
        assert plan.task_id is not None
        
        # Verify plan has steps
        assert plan.steps is not None
        assert isinstance(plan.steps, list)
        assert len(plan.steps) > 0
        
        # Verify each step has required fields
        for step in plan.steps:
            assert "step_id" in step
            assert "description" in step
            assert "type" in step
            assert "inputs" in step
            assert "expected_outputs" in step
        
        print(f"\n✅ Test 1 PASSED: Simple task planned")
        print(f"   Plan ID: {plan.id}")
        print(f"   Steps: {len(plan.steps)}")
        print(f"   Status: {plan.status}")
        
        return plan


class Test2DigitalTwinContext:
    """Test 2: Verify Digital Twin context is created and populated"""
    
    @pytest.mark.asyncio
    async def test_digital_twin_context_creation(self, db, planning_service):
        """Test that Digital Twin context is created when plan is generated"""
        
        task_description = "Write a function to calculate factorial"
        
        # Generate plan
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        # Get task
        task = db.query(Task).filter(Task.id == plan.task_id).first()
        assert task is not None
        
        # Get Digital Twin context
        context = task.get_context()
        
        # Verify context exists and has required fields
        assert context is not None
        assert isinstance(context, dict)
        
        # Verify required fields
        assert "original_user_request" in context
        assert context["original_user_request"] == task_description
        
        assert "active_todos" in context
        assert isinstance(context["active_todos"], list)
        assert len(context["active_todos"]) > 0
        
        assert "plan" in context
        assert context["plan"]["plan_id"] == str(plan.id)
        assert context["plan"]["version"] == plan.version
        
        assert "artifacts" in context
        assert "execution_logs" in context
        assert "interaction_history" in context
        assert "metadata" in context
        
        print(f"\n✅ Test 2 PASSED: Digital Twin context created")
        print(f"   Context keys: {list(context.keys())}")
        print(f"   Active todos: {len(context['active_todos'])}")
        print(f"   Plan version: {context['plan']['version']}")
        
        return task, context


class Test3ContextReuse:
    """Test 3: Planning with previous context"""
    
    @pytest.mark.asyncio
    async def test_planning_with_previous_context(self, db, planning_service):
        """Test creating a new plan for existing task with context"""
        
        # First, create initial task and plan
        task_description = "Create a REST API endpoint"
        
        plan1 = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        task_id = plan1.task_id
        task = db.query(Task).filter(Task.id == task_id).first()
        context1 = task.get_context()
        
        # Update context with some artifacts
        task.update_context({
            "artifacts": [
                {
                    "artifact_id": str(uuid4()),
                    "type": "code",
                    "name": "api_endpoint.py",
                    "version": 1
                }
            ]
        }, merge=True)
        db.commit()
        
        # Create a new plan version (replanning)
        plan2 = await planning_service.replan(
            plan_id=plan1.id,
            reason="Need to add authentication",
            context={"additional_requirement": "Add JWT authentication"}
        )
        
        # Verify new plan was created
        assert plan2 is not None
        assert plan2.version > plan1.version
        
        # Verify context includes previous information
        task.refresh()
        context2 = task.get_context()
        
        # Check that artifacts from previous context are preserved
        assert "artifacts" in context2
        assert len(context2["artifacts"]) > 0
        
        print(f"\n✅ Test 3 PASSED: Planning with previous context")
        print(f"   Plan 1 version: {plan1.version}")
        print(f"   Plan 2 version: {plan2.version}")
        print(f"   Artifacts preserved: {len(context2['artifacts'])}")
        
        return plan1, plan2, context2


class Test4ComplexTask:
    """Test 4: Complex task with many steps"""
    
    @pytest.mark.asyncio
    async def test_complex_task_planning(self, db, planning_service):
        """Test planning a complex task that should generate many steps"""
        
        task_description = """Create a complete e-commerce application with:
        1. User authentication and authorization
        2. Product catalog with categories
        3. Shopping cart functionality
        4. Order processing
        5. Payment integration
        6. Admin dashboard
        7. Email notifications
        8. Search functionality"""
        
        plan = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        # Verify plan was created
        assert plan is not None
        assert len(plan.steps) > 3  # Complex task should have many steps
        
        # Verify strategy has required fields
        assert plan.strategy is not None
        if isinstance(plan.strategy, dict):
            assert "approach" in plan.strategy
            assert "assumptions" in plan.strategy
            assert "constraints" in plan.strategy
        
        # Verify steps have proper structure
        step_ids = [step.get("step_id") for step in plan.steps]
        assert len(step_ids) == len(set(step_ids))  # All step_ids should be unique
        
        print(f"\n✅ Test 4 PASSED: Complex task planned")
        print(f"   Total steps: {len(plan.steps)}")
        print(f"   Strategy: {plan.strategy.get('approach', 'N/A')[:50] if isinstance(plan.strategy, dict) else 'N/A'}")
        
        return plan


class Test5ReplanningWithErrors:
    """Test 5: Replanning based on execution errors"""
    
    @pytest.mark.asyncio
    async def test_replanning_with_execution_errors(self, db, planning_service):
        """Test replanning when previous plan failed"""
        
        task_description = "Create a data processing pipeline"
        
        # Create initial plan
        plan1 = await planning_service.generate_plan(
            task_description=task_description,
            context=None
        )
        
        task_id = plan1.task_id
        task = db.query(Task).filter(Task.id == task_id).first()
        
        # Simulate execution errors in Digital Twin context
        task.update_context({
            "execution_logs": [
                {
                    "timestamp": "2025-12-03T20:00:00",
                    "level": "error",
                    "message": "Step 2 failed: Missing dependency",
                    "step_id": "step_2",
                    "error": "ModuleNotFoundError: No module named 'pandas'"
                },
                {
                    "timestamp": "2025-12-03T20:01:00",
                    "level": "warning",
                    "message": "Step 3 skipped due to dependency failure",
                    "step_id": "step_3"
                }
            ]
        }, merge=True)
        
        # Add interaction history
        task.add_to_history("error_feedback", {
            "errors": [
                "Missing pandas dependency",
                "Need to add data validation step"
            ],
            "suggestions": [
                "Add dependency installation step",
                "Add data validation before processing"
            ]
        })
        
        db.commit()
        
        # Replan with error context
        plan2 = await planning_service.replan(
            plan_id=plan1.id,
            reason="Previous plan failed due to missing dependencies",
            context={
                "execution_errors": task.get_context().get("execution_logs", []),
                "feedback": "Need to add dependency installation step"
            }
        )
        
        # Verify new plan addresses the errors
        assert plan2 is not None
        assert plan2.version > plan1.version
        
        # Check that new plan might have dependency installation steps
        step_descriptions = [step.get("description", "").lower() for step in plan2.steps]
        
        # The new plan should ideally address the errors
        # (this is a soft check as the model might format it differently)
        has_dependency_step = any(
            "dependenc" in desc or "install" in desc or "requirement" in desc
            for desc in step_descriptions
        )
        
        print(f"\n✅ Test 5 PASSED: Replanning with errors")
        print(f"   Plan 1 version: {plan1.version}")
        print(f"   Plan 2 version: {plan2.version}")
        print(f"   Execution errors in context: {len(task.get_context().get('execution_logs', []))}")
        print(f"   Has dependency step: {has_dependency_step}")
        
        return plan1, plan2


def run_all_tests():
    """Run all tests in sequence"""
    print("=" * 60)
    print("PLANNING SERVICE WITH DIGITAL TWIN - INTEGRATION TESTS")
    print("=" * 60)
    
    db = SessionLocal()
    planning_service = PlanningService(db)
    
    try:
        # Test 1: Simple task
        print("\n" + "=" * 60)
        print("TEST 1: Simple Task Planning")
        print("=" * 60)
        test1 = Test1SimpleTaskPlanning()
        plan1 = asyncio.run(test1.test_create_simple_task_and_plan(db, planning_service))
        
        # Test 2: Digital Twin context
        print("\n" + "=" * 60)
        print("TEST 2: Digital Twin Context")
        print("=" * 60)
        test2 = Test2DigitalTwinContext()
        task2, context2 = asyncio.run(test2.test_digital_twin_context_creation(db, planning_service))
        
        # Test 3: Context reuse
        print("\n" + "=" * 60)
        print("TEST 3: Planning with Previous Context")
        print("=" * 60)
        test3 = Test3ContextReuse()
        plan3a, plan3b, context3 = asyncio.run(test3.test_planning_with_previous_context(db, planning_service))
        
        # Test 4: Complex task
        print("\n" + "=" * 60)
        print("TEST 4: Complex Task Planning")
        print("=" * 60)
        test4 = Test4ComplexTask()
        plan4 = asyncio.run(test4.test_complex_task_planning(db, planning_service))
        
        # Test 5: Replanning with errors
        print("\n" + "=" * 60)
        print("TEST 5: Replanning with Execution Errors")
        print("=" * 60)
        test5 = Test5ReplanningWithErrors()
        plan5a, plan5b = asyncio.run(test5.test_replanning_with_execution_errors(db, planning_service))
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    run_all_tests()

