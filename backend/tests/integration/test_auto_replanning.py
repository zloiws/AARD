"""
Integration tests for automatic replanning on failure
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.models.plan import Plan
from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService
from app.services.reflection_service import ReflectionService


@pytest.mark.asyncio
async def test_handle_plan_failure_creates_new_plan(db: Session):
    """Test that _handle_plan_failure creates a new plan"""
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task that will fail",
        status=TaskStatus.APPROVED,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Create a plan
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task that will fail",
        steps=[
            {
                "step_id": "1",
                "description": "Step that will fail",
                "action": "test"
            }
        ],
        status="approved"
    )
    db.add(plan)
    db.commit()
    
    # Mark plan as failed
    plan.status = "failed"
    db.commit()
    
    # Test _handle_plan_failure
    execution_service = ExecutionService(db)
    new_plan = await execution_service._handle_plan_failure(
        plan=plan,
        error_message="Test error",
        execution_context={}
    )
    
    # Should create a new plan
    assert new_plan is not None
    assert new_plan.version == plan.version + 1
    assert new_plan.task_id == plan.task_id


@pytest.mark.asyncio
async def test_task_status_updated_to_failed(db: Session):
    """Test that task status is updated to FAILED when plan fails"""
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.IN_PROGRESS,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Create a plan
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task",
        steps=[],
        status="executing"
    )
    db.add(plan)
    db.commit()
    
    # Mark plan as failed
    plan.status = "failed"
    db.commit()
    
    # Test _handle_plan_failure
    execution_service = ExecutionService(db)
    await execution_service._handle_plan_failure(
        plan=plan,
        error_message="Test error",
        execution_context={}
    )
    
    # Refresh task
    db.refresh(task)
    assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_reflection_service_integration(db: Session):
    """Test that ReflectionService is used to analyze failure"""
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.APPROVED,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Create a plan
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task",
        steps=[],
        status="approved"
    )
    db.add(plan)
    db.commit()
    
    # Mark plan as failed
    plan.status = "failed"
    db.commit()
    
    # Test reflection analysis
    reflection_service = ReflectionService(db)
    reflection_result = await reflection_service.analyze_failure(
        task_description=task.description,
        error="Test error message",
        context={"plan_id": str(plan.id)},
        agent_id=None
    )
    
    assert reflection_result is not None
    assert "analysis" in reflection_result.to_dict()
    assert reflection_result.analysis.get("error_type") is not None


@pytest.mark.asyncio
async def test_replan_with_error_context(db: Session):
    """Test that replan includes error context"""
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.APPROVED,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Create a plan
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task",
        steps=[],
        status="approved"
    )
    db.add(plan)
    db.commit()
    
    # Test replan with error context
    planning_service = PlanningService(db)
    new_plan = await planning_service.replan(
        plan_id=plan.id,
        reason="Test failure",
        context={
            "error_analysis": {"error_type": "test_error"},
            "fix_suggestion": {"message": "Test fix"},
            "failed_at_step": 0
        }
    )
    
    assert new_plan is not None
    assert new_plan.version == plan.version + 1

