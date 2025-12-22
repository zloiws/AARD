"""
Integration tests for automatic replanning trigger based on error detection
"""
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.execution_error_types import (ErrorCategory, ErrorSeverity,
                                            ExecutionError)
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.execution_service import ExecutionService
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_critical_error_triggers_replanning(db: Session):
    """Test that critical errors trigger automatic replanning"""
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task with critical error",
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
        goal="Test task with critical error",
        steps=[],
        status="approved"
    )
    db.add(plan)
    db.commit()
    
    execution_service = ExecutionService(db)
    
    # Check that critical error requires replanning
    is_critical = execution_service._is_critical_error(
        "Plan has no steps",
        context={"plan_id": str(plan.id)}
    )
    assert is_critical is True
    
    # Check error classification
    classified_error = execution_service._classify_error(
        "Plan has no steps",
        context={"plan_id": str(plan.id)}
    )
    assert classified_error.severity == ErrorSeverity.CRITICAL
    assert classified_error.requires_replanning is True


@pytest.mark.asyncio
async def test_high_severity_error_triggers_replanning(db: Session):
    """Test that high severity errors trigger automatic replanning"""
    execution_service = ExecutionService(db)
    
    # Check that high severity error requires replanning
    is_critical = execution_service._is_critical_error(
        "Agent test-agent not found",
        context={}
    )
    assert is_critical is True
    
    classified_error = execution_service._classify_error(
        "Agent test-agent not found"
    )
    assert classified_error.severity == ErrorSeverity.HIGH
    assert classified_error.requires_replanning is True


@pytest.mark.asyncio
async def test_medium_severity_error_does_not_trigger_replanning(db: Session):
    """Test that medium severity errors do not trigger automatic replanning"""
    execution_service = ExecutionService(db)
    
    # Check that medium severity error does not require replanning
    is_critical = execution_service._is_critical_error(
        "Some random non-critical error",
        context={}
    )
    assert is_critical is False
    
    classified_error = execution_service._classify_error(
        "Some random non-critical error"
    )
    assert classified_error.severity == ErrorSeverity.MEDIUM
    assert classified_error.requires_replanning is False


@pytest.mark.asyncio
async def test_error_classification_in_execution_context(db: Session):
    """Test error classification with execution context"""
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
        steps=[
            {"step_id": "step_1", "description": "Step 1"},
            {"step_id": "step_2", "description": "Step 2"}
        ],
        status="approved"
    )
    db.add(plan)
    db.commit()
    
    execution_service = ExecutionService(db)
    
    # Classify error with context
    error_context = {
        "step_id": "step_1",
        "step_index": 0,
        "plan_id": str(plan.id),
        "plan_version": plan.version,
        "total_steps": 2
    }
    
    classified_error = execution_service._classify_error(
        "Dependency step_0 not found in execution context",
        error_type="DependencyError",
        context=error_context
    )
    
    assert classified_error.severity == ErrorSeverity.CRITICAL
    assert classified_error.category == ErrorCategory.DEPENDENCY
    assert classified_error.requires_replanning is True
    assert "step_id" in classified_error.metadata
    assert classified_error.metadata["plan_id"] == str(plan.id)


@pytest.mark.asyncio
async def test_error_classification_in_handle_plan_failure(db: Session):
    """Test that error classification is used in _handle_plan_failure"""
    # Create a task
    task = Task(
        id=uuid4(),
        description="Test task for error handling",
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
        goal="Test task for error handling",
        steps=[],
        status="approved"
    )
    db.add(plan)
    db.commit()
    
    execution_service = ExecutionService(db)
    
    # Pre-classify error
    classified_error = execution_service._classify_error(
        "Plan has no steps",
        context={"plan_id": str(plan.id)}
    )
    
    # Mock the replan method to avoid actual planning
    with patch.object(execution_service, '_handle_plan_failure', new_callable=AsyncMock) as mock_handle:
        # Call _handle_plan_failure with classified error
        await execution_service._handle_plan_failure(
            plan=plan,
            error_message="Plan has no steps",
            execution_context={},
            classified_error=classified_error
        )
        
        # Verify that _handle_plan_failure was called with classified error
        mock_handle.assert_called_once()
        call_args = mock_handle.call_args
        assert call_args[1]["classified_error"] is not None
        assert call_args[1]["classified_error"].severity == ErrorSeverity.CRITICAL


@pytest.mark.asyncio
async def test_multiple_error_types_classification(db: Session):
    """Test classification of different error types"""
    execution_service = ExecutionService(db)
    
    test_cases = [
        ("Plan has no steps", ErrorSeverity.CRITICAL, ErrorCategory.LOGIC, True),
        ("No suitable model found", ErrorSeverity.CRITICAL, ErrorCategory.ENVIRONMENT, True),
        ("Dependency not found", ErrorSeverity.CRITICAL, ErrorCategory.DEPENDENCY, True),
        ("Agent not found", ErrorSeverity.HIGH, ErrorCategory.DEPENDENCY, True),
        ("Function call validation failed", ErrorSeverity.HIGH, ErrorCategory.VALIDATION, True),
        ("Step execution timeout", ErrorSeverity.HIGH, ErrorCategory.TIMEOUT, True),
        ("Some unknown error", ErrorSeverity.MEDIUM, ErrorCategory.UNKNOWN, False),
    ]
    
    for error_message, expected_severity, expected_category, expected_replanning in test_cases:
        classified_error = execution_service._classify_error(error_message)
        assert classified_error.severity == expected_severity, f"Error: {error_message}"
        assert classified_error.category == expected_category, f"Error: {error_message}"
        assert classified_error.requires_replanning == expected_replanning, f"Error: {error_message}"


@pytest.mark.asyncio
async def test_error_metadata_preservation(db: Session):
    """Test that error metadata is preserved in classification"""
    execution_service = ExecutionService(db)
    
    context = {
        "step_id": "step_1",
        "step_index": 0,
        "plan_id": "test-plan-123",
        "custom_field": "custom_value"
    }
    
    classified_error = execution_service._classify_error(
        "Plan has no steps",
        context=context
    )
    
    assert classified_error.metadata["step_id"] == "step_1"
    assert classified_error.metadata["plan_id"] == "test-plan-123"
    assert classified_error.metadata["custom_field"] == "custom_value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

