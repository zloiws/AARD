"""
Integration tests for checkpoint API with execution service
"""
import pytest
from fastapi.testclient import TestClient
from uuid import uuid4
from sqlalchemy.orm import Session

from app.main import app
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.core.database import SessionLocal

client = TestClient(app)


@pytest.fixture
def db():
    """Database session fixture"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_plan(db: Session):
    """Create a sample plan for testing"""
    task = Task(
        id=uuid4(),
        description="Test task for checkpoint integration",
        status=TaskStatus.APPROVED,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test checkpoint integration",
        steps=[
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            }
        ],
        status="approved"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    return plan


class TestCheckpointAPIIntegration:
    """Integration tests for checkpoint API"""
    
    def test_create_checkpoint_via_api(self, db: Session, sample_plan: Plan):
        """Test creating checkpoint via API"""
        checkpoint_data = {
            "entity_type": "plan",
            "entity_id": str(sample_plan.id),
            "state_data": {
                "status": "executing",
                "current_step": 0
            },
            "reason": "Test checkpoint",
            "created_by": "test_user"
        }
        
        response = client.post("/api/checkpoints/", json=checkpoint_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["entity_type"] == "plan"
        assert data["entity_id"] == str(sample_plan.id)
        assert data["reason"] == "Test checkpoint"
        assert "id" in data
    
    def test_list_checkpoints_for_plan(self, db: Session, sample_plan: Plan):
        """Test listing checkpoints for a plan"""
        from app.services.checkpoint_service import CheckpointService
        
        # Create a checkpoint first
        service = CheckpointService(db)
        checkpoint = service.create_plan_checkpoint(
            sample_plan,
            reason="Test checkpoint for listing"
        )
        
        # List checkpoints via API
        response = client.get(
            "/api/checkpoints/",
            params={
                "entity_type": "plan",
                "entity_id": str(sample_plan.id),
                "limit": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert len(data) >= 1
        assert data[0]["entity_type"] == "plan"
        assert data[0]["entity_id"] == str(sample_plan.id)
    
    def test_get_checkpoint_by_id(self, db: Session, sample_plan: Plan):
        """Test getting checkpoint by ID"""
        from app.services.checkpoint_service import CheckpointService
        
        # Create a checkpoint
        service = CheckpointService(db)
        checkpoint = service.create_plan_checkpoint(
            sample_plan,
            reason="Test checkpoint"
        )
        
        # Get checkpoint via API
        response = client.get(f"/api/checkpoints/{checkpoint.id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == str(checkpoint.id)
        assert "state_data" in data
        assert data["state_data"]["status"] == sample_plan.status
    
    def test_restore_checkpoint_via_api(self, db: Session, sample_plan: Plan):
        """Test restoring checkpoint via API"""
        from app.services.checkpoint_service import CheckpointService
        
        # Create a checkpoint
        service = CheckpointService(db)
        checkpoint = service.create_plan_checkpoint(
            sample_plan,
            reason="Test checkpoint for restore"
        )
        
        # Restore checkpoint via API
        response = client.post(f"/api/checkpoints/{checkpoint.id}/restore")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "restored"
        assert data["checkpoint_id"] == str(checkpoint.id)
        assert "state_data" in data
    
    def test_get_latest_checkpoint(self, db: Session, sample_plan: Plan):
        """Test getting latest checkpoint for an entity"""
        from app.services.checkpoint_service import CheckpointService
        
        # Create multiple checkpoints
        service = CheckpointService(db)
        checkpoint1 = service.create_plan_checkpoint(
            sample_plan,
            reason="First checkpoint"
        )
        
        # Update plan and create second checkpoint
        sample_plan.current_step = 1
        db.commit()
        checkpoint2 = service.create_plan_checkpoint(
            sample_plan,
            reason="Second checkpoint"
        )
        
        # Get latest checkpoint via API
        response = client.get(
            f"/api/checkpoints/plan/{sample_plan.id}/latest"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Latest should be checkpoint2
        assert data["id"] == str(checkpoint2.id)
        assert data["state_data"]["current_step"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
