"""
Integration tests for Dashboard API (Phase 1, Task 6.5)
"""
from uuid import uuid4

import pytest
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from sqlalchemy.orm import Session


def test_get_dashboard_tasks(db: Session, client):
    """Test GET /api/dashboard/tasks"""
    # Create test tasks
    task1 = Task(
        id=uuid4(),
        description="Task 1 - Pending Approval",
        status=TaskStatus.PENDING_APPROVAL,
        created_by_role="planner",
        priority=5,
        autonomy_level=2
    )
    task2 = Task(
        id=uuid4(),
        description="Task 2 - In Progress",
        status=TaskStatus.IN_PROGRESS,
        created_by_role="planner",
        priority=7,
        autonomy_level=3
    )
    task3 = Task(
        id=uuid4(),
        description="Task 3 - On Hold",
        status=TaskStatus.ON_HOLD,
        created_by_role="human",
        priority=3,
        autonomy_level=1
    )
    
    db.add_all([task1, task2, task3])
    db.commit()
    
    # Test API endpoint
    response = client.get("/api/dashboard/tasks")
    assert response.status_code == 200
    
    data = response.json()
    assert "tasks" in data
    assert "statistics" in data
    
    # Check statistics
    stats = data["statistics"]
    assert stats["pending_approval"] >= 1
    assert stats["in_progress"] >= 1
    assert stats["on_hold"] >= 1
    
    # Check tasks
    tasks = data["tasks"]
    assert len(tasks) >= 3
    
    # Verify task structure
    task = tasks[0]
    assert "id" in task
    assert "description" in task
    assert "status" in task
    assert "priority" in task
    assert "autonomy_level" in task


def test_get_dashboard_tasks_with_status_filter(db: Session, client):
    """Test GET /api/dashboard/tasks with status filter"""
    # Create test task
    task = Task(
        id=uuid4(),
        description="Filtered task",
        status=TaskStatus.PENDING_APPROVAL,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    
    # Test with status filter
    response = client.get("/api/dashboard/tasks?status=pending_approval")
    assert response.status_code == 200
    
    data = response.json()
    tasks = data["tasks"]
    
    # All tasks should be pending_approval
    for task_data in tasks:
        assert task_data["status"] == "pending_approval"


def test_get_plan_history(db: Session, client):
    """Test GET /api/dashboard/plan-history/{plan_id}"""
    # Create task and plan
    task = Task(
        id=uuid4(),
        description="Test task for plan history",
        status=TaskStatus.DRAFT,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test plan",
        steps=[],
        status="draft",
        agent_metadata={"agent_id": str(uuid4())}
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    # Test API endpoint
    response = client.get(f"/api/dashboard/plan-history/{plan.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)


def test_cancel_task(db: Session, client):
    """Test POST /api/dashboard/tasks/{task_id}/cancel"""
    # Create task in progress
    task = Task(
        id=uuid4(),
        description="Task to cancel",
        status=TaskStatus.IN_PROGRESS,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create active plan
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Task to cancel",
        steps=[],
        status="executing"
    )
    db.add(plan)
    db.commit()
    
    # Test cancellation
    response = client.post(f"/api/dashboard/tasks/{task.id}/cancel")
    assert response.status_code == 200
    
    data = response.json()
    assert data["message"] == "Task cancelled successfully"
    assert data["task_id"] == str(task.id)
    
    # Verify task status
    db.refresh(task)
    assert task.status == TaskStatus.CANCELLED
    
    # Verify plan status
    db.refresh(plan)
    assert plan.status == "cancelled"


def test_cancel_task_invalid_status(db: Session, client):
    """Test that cancelling a completed task fails"""
    # Create completed task
    task = Task(
        id=uuid4(),
        description="Completed task",
        status=TaskStatus.COMPLETED,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Test cancellation (should fail)
    response = client.post(f"/api/dashboard/tasks/{task.id}/cancel")
    assert response.status_code == 400


def test_create_task_manual(db: Session, client):
    """Test POST /api/dashboard/tasks/create"""
    # Test task creation
    response = client.post(
        "/api/dashboard/tasks/create",
        json={
            "description": "Manually created task",
            "priority": 6,
            "autonomy_level": 2
        }
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "id" in data
    assert data["description"] == "Manually created task"
    assert data["status"] == "draft"
    assert data["priority"] == 6
    assert data["autonomy_level"] == 2
    
    # Verify task was created in database
    task_id = data["id"]
    task = db.query(Task).filter(Task.id == task_id).first()
    assert task is not None
    assert task.description == "Manually created task"
    assert task.status == TaskStatus.DRAFT
    assert task.created_by_role == "human"


def test_create_task_manual_invalid_priority(db: Session, client):
    """Test that creating task with invalid priority fails"""
    response = client.post(
        "/api/dashboard/tasks/create",
        json={
            "description": "Task with invalid priority",
            "priority": 10,  # Invalid (> 9)
            "autonomy_level": 2
        }
    )
    assert response.status_code == 400


def test_create_task_manual_invalid_autonomy(db: Session, client):
    """Test that creating task with invalid autonomy level fails"""
    response = client.post(
        "/api/dashboard/tasks/create",
        json={
            "description": "Task with invalid autonomy",
            "priority": 5,
            "autonomy_level": 5  # Invalid (> 4)
        }
    )
    assert response.status_code == 400


def test_dashboard_statistics(db: Session, client):
    """Test that dashboard statistics are calculated correctly"""
    # Create tasks with different statuses
    tasks = [
        Task(id=uuid4(), description=f"Task {i}", status=TaskStatus.PENDING_APPROVAL, created_by_role="planner")
        for i in range(3)
    ]
    tasks.extend([
        Task(id=uuid4(), description=f"Task {i}", status=TaskStatus.IN_PROGRESS, created_by_role="planner")
        for i in range(2)
    ])
    tasks.append(
        Task(id=uuid4(), description="Failed task", status=TaskStatus.FAILED, created_by_role="planner")
    )
    
    db.add_all(tasks)
    db.commit()
    
    # Get dashboard data
    response = client.get("/api/dashboard/tasks")
    assert response.status_code == 200
    
    data = response.json()
    stats = data["statistics"]
    
    assert stats["pending_approval"] >= 3
    assert stats["in_progress"] >= 2
    assert stats["failed"] >= 1

