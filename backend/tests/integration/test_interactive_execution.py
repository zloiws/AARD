"""
Integration tests for InteractiveExecutionService
"""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.interactive_execution_service import InteractiveExecutionService, ExecutionState


@pytest.fixture
def test_plan_id() -> uuid4:
    """Create a test plan ID"""
    return uuid4()


def test_pause_for_clarification(db: Session, test_plan_id: uuid4):
    """Test pausing execution for clarification"""
    service = InteractiveExecutionService(db)
    
    result = service.pause_for_clarification(
        plan_id=test_plan_id,
        step_id="step_1",
        question="Do you want to proceed?"
    )
    
    assert result["state"] == ExecutionState.WAITING_CLARIFICATION.value
    assert "question" in result
    assert "paused_at" in result


def test_apply_human_correction(db: Session, test_plan_id: uuid4):
    """Test applying human correction"""
    service = InteractiveExecutionService(db)
    
    # First pause
    service.pause_for_clarification(test_plan_id, "step_1", "Question?")
    
    # Apply correction
    correction = {"updated_step": {"description": "Updated description"}}
    result = service.apply_human_correction(test_plan_id, "step_1", correction)
    
    assert result["status"] == "correction_applied"
    assert result["correction"] == correction


def test_resume_execution(db: Session, test_plan_id: uuid4):
    """Test resuming execution"""
    service = InteractiveExecutionService(db)
    
    # First pause
    service.pause_for_clarification(test_plan_id, "step_1", "Question?")
    
    # Resume
    result = service.resume_execution(test_plan_id, feedback="Proceed")
    
    assert result["status"] == "resumed"
    assert result["state"] == ExecutionState.RESUMED.value


def test_get_execution_state(db: Session, test_plan_id: uuid4):
    """Test getting execution state"""
    service = InteractiveExecutionService(db)
    
    # Pause first
    service.pause_for_clarification(test_plan_id, "step_1", "Question?")
    
    # Get state
    state = service.get_execution_state(test_plan_id)
    
    assert state is not None
    assert state["state"] == ExecutionState.WAITING_CLARIFICATION.value
    assert state["step_id"] == "step_1"


def test_clear_execution_state(db: Session, test_plan_id: uuid4):
    """Test clearing execution state"""
    service = InteractiveExecutionService(db)
    
    # Create state
    service.pause_for_clarification(test_plan_id, "step_1", "Question?")
    
    # Clear
    result = service.clear_execution_state(test_plan_id)
    
    assert result is True
    
    # Verify cleared
    state = service.get_execution_state(test_plan_id)
    assert state is None

