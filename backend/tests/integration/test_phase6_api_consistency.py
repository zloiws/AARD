"""
API consistency tests for Phase 6 (A/B Testing)
"""
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

# Add backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
# Import app after path setup
from main import app


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
def db():
    """Database session fixture"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_task(db):
    """Create a test task"""
    task = Task(
        id=uuid4(),
        description="Test task for API consistency",
        status=TaskStatus.PENDING,
        priority=5
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def test_create_plan_api_backward_compatibility(client, test_task):
    """Test that POST /api/plans/ works without new parameters"""
    response = client.post(
        "/api/plans/",
        json={
            "task_description": "Create a simple API",
            "task_id": str(test_task.id)
        }
    )
    
    # Should work without errors
    assert response.status_code in [200, 201]
    data = response.json()
    assert "id" in data
    assert "goal" in data


def test_create_plan_api_with_context(client, test_task):
    """Test that POST /api/plans/ works with context"""
    response = client.post(
        "/api/plans/",
        json={
            "task_description": "Create a REST API",
            "task_id": str(test_task.id),
            "context": {
                "constraints": ["Must use FastAPI"],
                "requirements": ["Authentication required"]
            }
        }
    )
    
    # Should work with context
    assert response.status_code in [200, 201]
    data = response.json()
    assert "id" in data


def test_list_plans_api(client):
    """Test that GET /api/plans/ works"""
    response = client.get("/api/plans/")
    
    # Should return list of plans
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_plan_api(client, test_task):
    """Test that GET /api/plans/{plan_id} works"""
    # First create a plan
    create_response = client.post(
        "/api/plans/",
        json={
            "task_description": "Test plan",
            "task_id": str(test_task.id)
        }
    )
    
    if create_response.status_code not in [200, 201]:
        pytest.skip("Failed to create plan for testing")
    
    plan_id = create_response.json()["id"]
    
    # Then get it
    response = client.get(f"/api/plans/{plan_id}")
    
    # Should return plan
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == plan_id


def test_replan_api(client, test_task):
    """Test that POST /api/plans/{plan_id}/replan works"""
    # First create a plan
    create_response = client.post(
        "/api/plans/",
        json={
            "task_description": "Initial plan",
            "task_id": str(test_task.id)
        }
    )
    
    if create_response.status_code not in [200, 201]:
        pytest.skip("Failed to create plan for testing")
    
    plan_id = create_response.json()["id"]
    
    # Approve plan
    client.post(f"/api/plans/{plan_id}/approve")
    
    # Then replan
    response = client.post(
        f"/api/plans/{plan_id}/replan",
        json={
            "reason": "Test replanning",
            "context": {"updated": True}
        }
    )
    
    # Should create new plan
    assert response.status_code in [200, 201]
    data = response.json()
    assert "id" in data
    assert data["id"] != plan_id  # Should be a new plan


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

