"""
Integration tests for extended task lifecycle
"""
from uuid import uuid4

import pytest
from app.models.task import Task, TaskStatus
from sqlalchemy.orm import Session


def test_task_status_enum():
    """Test that all TaskStatus values are available"""
    assert TaskStatus.DRAFT == "draft"
    assert TaskStatus.PENDING_APPROVAL == "pending_approval"
    assert TaskStatus.APPROVED == "approved"
    assert TaskStatus.IN_PROGRESS == "in_progress"
    assert TaskStatus.ON_HOLD == "on_hold"
    assert TaskStatus.CANCELLED == "cancelled"
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.COMPLETED == "completed"
    assert TaskStatus.FAILED == "failed"


def test_task_with_new_fields(db: Session):
    """Test creating task with new workflow fields"""
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.DRAFT,
        created_by_role="planner",
        autonomy_level=2
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    assert task.status == TaskStatus.DRAFT
    assert task.created_by_role == "planner"
    assert task.autonomy_level == 2
    assert task.approved_by_role is None


def test_task_approval_workflow(db: Session):
    """Test task approval workflow"""
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.DRAFT,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Transition to PENDING_APPROVAL
    task.status = TaskStatus.PENDING_APPROVAL
    db.commit()
    db.refresh(task)
    assert task.status == TaskStatus.PENDING_APPROVAL
    
    # Approve
    task.status = TaskStatus.APPROVED
    task.approved_by = "user"
    task.approved_by_role = "human"
    db.commit()
    db.refresh(task)
    assert task.status == TaskStatus.APPROVED
    assert task.approved_by_role == "human"


def test_task_autonomy_levels(db: Session):
    """Test different autonomy levels"""
    for level in range(5):
        task = Task(
            id=uuid4(),
            description=f"Test task level {level}",
            status=TaskStatus.DRAFT,
            autonomy_level=level
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        assert task.autonomy_level == level


def test_task_on_hold_status(db: Session):
    """Test ON_HOLD status"""
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.IN_PROGRESS,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Put on hold
    task.status = TaskStatus.ON_HOLD
    db.commit()
    db.refresh(task)
    assert task.status == TaskStatus.ON_HOLD


def test_task_cancelled_status(db: Session):
    """Test CANCELLED status"""
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.IN_PROGRESS,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Cancel
    task.status = TaskStatus.CANCELLED
    db.commit()
    db.refresh(task)
    assert task.status == TaskStatus.CANCELLED

