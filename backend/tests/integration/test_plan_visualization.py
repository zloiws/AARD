"""
Integration tests for plan visualization
"""
from uuid import uuid4

import pytest
from app.core.database import SessionLocal
from app.main import app
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
def hierarchical_plan(db: Session):
    """Create a plan with hierarchical steps"""
    task = Task(
        id=uuid4(),
        description="Test task for visualization",
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
        goal="Test hierarchical plan",
        steps=[
            {
                "step_id": "step_1",
                "description": "Root step",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "description": "Child step 1",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_3",
                "description": "Child step 2",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_4",
                "description": "Grandchild step",
                "type": "action",
                "dependencies": ["step_2", "step_3"]
            }
        ],
        status="approved"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    return plan


class TestPlanVisualizationIntegration:
    """Integration tests for plan visualization"""
    
    def test_tree_api_with_hierarchical_plan(self, db: Session, hierarchical_plan: Plan):
        """Test tree API endpoint with hierarchical plan"""
        response = client.get(f"/api/plans/{hierarchical_plan.id}/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_steps"] == 4
        assert data["total_levels"] == 3
        assert data["has_hierarchy"] is True
        assert len(data["root_nodes"]) == 1
        
        root = data["root_nodes"][0]
        assert root["step_id"] == "step_1"
        assert len(root["children"]) == 2
    
    def test_tree_service_with_plan_steps(self, db: Session, hierarchical_plan: Plan):
        """Test tree service with actual plan steps"""
        from app.services.plan_tree_service import PlanTreeService
        
        steps = hierarchical_plan.steps
        if isinstance(steps, str):
            import json
            steps = json.loads(steps)
        
        tree_service = PlanTreeService()
        tree = tree_service.build_tree(steps)
        
        assert tree["total_steps"] == 4
        assert tree["total_levels"] == 3
        assert len(tree["root_nodes"]) == 1
    
    def test_tree_api_includes_plan_metadata(self, db: Session, hierarchical_plan: Plan):
        """Test that tree API includes plan metadata"""
        response = client.get(f"/api/plans/{hierarchical_plan.id}/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["plan_id"] == str(hierarchical_plan.id)
        assert data["plan_version"] == hierarchical_plan.version
        assert data["plan_status"] == hierarchical_plan.status
        assert data["plan_goal"] == hierarchical_plan.goal
    
    def test_tree_api_metadata_parameter(self, db: Session, hierarchical_plan: Plan):
        """Test tree API with include_metadata parameter"""
        # With metadata
        response = client.get(
            f"/api/plans/{hierarchical_plan.id}/tree",
            params={"include_metadata": "true"}
        )
        assert response.status_code == 200
        data = response.json()
        root = data["root_nodes"][0]
        # Should have metadata fields if they exist in steps
        assert "step_id" in root
        assert "description" in root
        
        # Without metadata
        response = client.get(
            f"/api/plans/{hierarchical_plan.id}/tree",
            params={"include_metadata": "false"}
        )
        assert response.status_code == 200
        # Should still work, just with minimal metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
