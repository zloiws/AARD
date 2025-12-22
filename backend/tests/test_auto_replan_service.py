"""
Tests for auto_replan_on_error method in PlanningService
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.execution_error_types import ErrorCategory, ErrorSeverity
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.planning_service import PlanningService
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_auto_replan_on_error_creates_new_plan(db: Session):
    """Test that auto_replan_on_error creates a new plan version"""
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task for auto replan",
        status=TaskStatus.APPROVED,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Create a plan
    original_plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task for auto replan",
        steps=[{"step_id": "step_1", "description": "Step 1"}],
        status="approved"
    )
    db.add(original_plan)
    db.commit()
    
    planning_service = PlanningService(db)
    
    # Mock replan to avoid actual LLM calls and DB operations
    with patch.object(planning_service, 'replan', new_callable=AsyncMock) as mock_replan:
        # Create mock new plan (already in DB session)
        new_plan = Plan(
            id=uuid4(),
            task_id=task.id,
            version=2,
            goal="Test task for auto replan",
            steps=[{"step_id": "step_1", "description": "Step 1 fixed"}],
            status="draft"
        )
        db.add(new_plan)
        db.commit()
        mock_replan.return_value = new_plan
        
        # Call auto_replan_on_error
        result = await planning_service.auto_replan_on_error(
            plan_id=original_plan.id,
            error_message="Step execution failed",
            error_severity="CRITICAL",
            error_category="LOGIC",
            failed_at_step=0
        )
        
        # Verify replan was called
        assert mock_replan.called
    
    # Verify result is not None
    assert result is not None


@pytest.mark.asyncio
async def test_auto_replan_on_error_with_classification(db: Session):
    """Test that auto_replan_on_error uses error classification"""
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
    
    planning_service = PlanningService(db)
    
    # Mock generate_plan
    with patch.object(planning_service, 'generate_plan', new_callable=AsyncMock) as mock_generate:
        new_plan = Plan(
            id=uuid4(),
            task_id=task.id,
            version=2,
            goal="Test task",
            steps=[],
            status="draft"
        )
        mock_generate.return_value = new_plan
        
        # Call without explicit severity/category (should auto-classify)
        result = await planning_service.auto_replan_on_error(
            plan_id=plan.id,
            error_message="Plan has no steps",
            failed_at_step=0
        )
        
        # Should still work with auto-classification
        assert mock_generate.called or result is not None


@pytest.mark.asyncio
async def test_auto_replan_on_error_includes_error_context(db: Session):
    """Test that auto_replan_on_error includes error context in replan"""
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
    
    planning_service = PlanningService(db)
    
    execution_context = {
        "step_1": {"status": "completed", "output": "result"},
        "step_2": {"status": "failed", "error": "Error occurred"}
    }
    
    # Mock generate_plan and check context
    with patch.object(planning_service, 'generate_plan', new_callable=AsyncMock) as mock_generate:
        new_plan = Plan(
            id=uuid4(),
            task_id=task.id,
            version=2,
            goal="Test task",
            steps=[],
            status="draft"
        )
        mock_generate.return_value = new_plan
        
        # Mock replan to check context
        with patch.object(planning_service, 'replan', new_callable=AsyncMock) as mock_replan:
            mock_replan.return_value = new_plan
            
            await planning_service.auto_replan_on_error(
                plan_id=plan.id,
                error_message="Test error",
                error_severity="CRITICAL",
                error_category="LOGIC",
                execution_context=execution_context,
                failed_at_step=1
            )
            
            # Verify replan was called with error context
            assert mock_replan.called
            call_kwargs = mock_replan.call_args[1]
            assert "context" in call_kwargs
            context = call_kwargs["context"]
            assert context.get("auto_replan") is True
            assert "error" in context
            assert context["error"]["severity"] == "CRITICAL"
            assert context["error"]["category"] == "LOGIC"
            assert context["error"]["failed_at_step"] == 1


@pytest.mark.asyncio
async def test_auto_replan_on_error_handles_failure(db: Session):
    """Test that auto_replan_on_error handles failures gracefully"""
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
    
    planning_service = PlanningService(db)
    
    # Mock replan to raise exception
    with patch.object(planning_service, 'replan', new_callable=AsyncMock) as mock_replan:
        mock_replan.side_effect = Exception("Replan failed")
        
        # Should return None on failure
        result = await planning_service.auto_replan_on_error(
            plan_id=plan.id,
            error_message="Test error",
            error_severity="CRITICAL",
            error_category="LOGIC"
        )
        
        assert result is None


@pytest.mark.asyncio
async def test_auto_replan_on_error_reason_formatting(db: Session):
    """Test that auto_replan_on_error formats reason correctly"""
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
    
    planning_service = PlanningService(db)
    
    # Mock replan to check reason
    with patch.object(planning_service, 'replan', new_callable=AsyncMock) as mock_replan:
        new_plan = Plan(
            id=uuid4(),
            task_id=task.id,
            version=2,
            goal="Test task",
            steps=[],
            status="draft"
        )
        mock_replan.return_value = new_plan
        
        await planning_service.auto_replan_on_error(
            plan_id=plan.id,
            error_message="Dependency not found: step_0",
            error_severity="CRITICAL",
            error_category="DEPENDENCY",
            failed_at_step=1
        )
        
        # Verify reason was passed correctly
        assert mock_replan.called
        call_kwargs = mock_replan.call_args[1]
        reason = call_kwargs.get("reason", "")
        assert "Автоматическое перепланирование" in reason
        assert "CRITICAL" in reason or "DEPENDENCY" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

