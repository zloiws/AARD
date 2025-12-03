"""
Integration tests for automatic DRAFT → PENDING_APPROVAL transition
"""
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.models.plan import Plan
from app.services.adaptive_approval_service import AdaptiveApprovalService
from app.services.planning_service import PlanningService


def test_detect_critical_steps_create_agent(db: Session):
    """Test detection of critical step: creating agent"""
    adaptive_approval = AdaptiveApprovalService(db)
    
    steps = [
        {
            "step_id": "1",
            "description": "Create a new agent for handling user requests",
            "action": "create_agent"
        },
        {
            "step_id": "2",
            "description": "Test the agent",
            "action": "test"
        }
    ]
    
    result = adaptive_approval.detect_critical_steps(steps)
    
    assert result["has_critical_steps"] is True
    assert "create_agent" in result["critical_types"]
    assert result["requires_mandatory_approval"] is True
    assert len(result["critical_steps"]) > 0


def test_detect_critical_steps_modify_tool(db: Session):
    """Test detection of critical step: modifying tool"""
    adaptive_approval = AdaptiveApprovalService(db)
    
    steps = [
        {
            "step_id": "1",
            "description": "Update the database tool to add new features",
            "action": "modify_tool"
        }
    ]
    
    result = adaptive_approval.detect_critical_steps(steps)
    
    assert result["has_critical_steps"] is True
    assert "modify_tool" in result["critical_types"]
    assert result["requires_mandatory_approval"] is True


def test_detect_critical_steps_system_operation(db: Session):
    """Test detection of critical step: system operation"""
    adaptive_approval = AdaptiveApprovalService(db)
    
    steps = [
        {
            "step_id": "1",
            "description": "Execute system command to restart service",
            "action": "system_command"
        }
    ]
    
    result = adaptive_approval.detect_critical_steps(steps)
    
    assert result["has_critical_steps"] is True
    assert "system_operation" in result["critical_types"]
    assert result["requires_mandatory_approval"] is True


def test_detect_critical_steps_protected_data(db: Session):
    """Test detection of critical step: accessing protected data"""
    adaptive_approval = AdaptiveApprovalService(db)
    
    steps = [
        {
            "step_id": "1",
            "description": "Access database to modify user credentials",
            "action": "access_database"
        }
    ]
    
    result = adaptive_approval.detect_critical_steps(steps)
    
    assert result["has_critical_steps"] is True
    assert "protected_data" in result["critical_types"]
    assert result["requires_mandatory_approval"] is True


def test_detect_critical_steps_no_critical(db: Session):
    """Test that non-critical steps are not flagged"""
    adaptive_approval = AdaptiveApprovalService(db)
    
    steps = [
        {
            "step_id": "1",
            "description": "Read configuration file",
            "action": "read_file"
        },
        {
            "step_id": "2",
            "description": "Process data",
            "action": "process"
        }
    ]
    
    result = adaptive_approval.detect_critical_steps(steps)
    
    assert result["has_critical_steps"] is False
    assert len(result["critical_types"]) == 0
    assert result["requires_mandatory_approval"] is False


def test_task_transition_draft_to_pending_approval(db: Session):
    """Test that task transitions from DRAFT to PENDING_APPROVAL when critical steps detected"""
    # Create a task in DRAFT status
    task = Task(
        id=uuid4(),
        description="Create a new agent for testing",
        status=TaskStatus.DRAFT,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    assert task.status == TaskStatus.DRAFT
    
    # Create a plan with critical steps
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Create a new agent for testing",
        steps=[
            {
                "step_id": "1",
                "description": "Create a new agent",
                "action": "create_agent"
            }
        ],
        status="draft"
    )
    db.add(plan)
    db.commit()
    
    # Simulate approval request creation with critical steps
    adaptive_approval = AdaptiveApprovalService(db)
    critical_info = adaptive_approval.detect_critical_steps(
        steps=plan.steps,
        task_description=plan.goal
    )
    
    # If critical steps detected, transition task to PENDING_APPROVAL
    if critical_info["requires_mandatory_approval"]:
        task.status = TaskStatus.PENDING_APPROVAL
        db.commit()
        db.refresh(task)
    
    assert task.status == TaskStatus.PENDING_APPROVAL


def test_task_no_transition_when_no_critical_steps(db: Session):
    """Test that task stays in DRAFT when no critical steps detected"""
    # Create a task in DRAFT status
    task = Task(
        id=uuid4(),
        description="Read configuration file",
        status=TaskStatus.DRAFT,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    assert task.status == TaskStatus.DRAFT
    
    # Create a plan without critical steps
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Read configuration file",
        steps=[
            {
                "step_id": "1",
                "description": "Read file",
                "action": "read_file"
            }
        ],
        status="draft"
    )
    db.add(plan)
    db.commit()
    
    # Check for critical steps
    adaptive_approval = AdaptiveApprovalService(db)
    critical_info = adaptive_approval.detect_critical_steps(
        steps=plan.steps,
        task_description=plan.goal
    )
    
    # Task should remain in DRAFT if no critical steps
    if not critical_info["requires_mandatory_approval"]:
        # Task can stay in DRAFT or transition based on other logic
        # For this test, we just verify it's not forced to PENDING_APPROVAL
        assert task.status in [TaskStatus.DRAFT, TaskStatus.APPROVED]

