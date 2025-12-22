"""
Tests for plan tree API endpoint
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
def sample_plan(db: Session):
    """Create a sample plan with steps for testing"""
    # Create task
    task = Task(
        id=uuid4(),
        description="Test task for tree visualization",
        status=TaskStatus.APPROVED,
        created_by_role="planner"
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create plan with hierarchical steps
    plan = Plan(
        id=uuid4(),
        task_id=task.id,
        version=1,
        goal="Test task for tree visualization",
        steps=[
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            },
            {
                "step_id": "step_2",
                "description": "Second step",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_3",
                "description": "Third step",
                "type": "action",
                "dependencies": ["step_1"]
            },
            {
                "step_id": "step_4",
                "description": "Fourth step",
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


class TestPlanTreeAPI:
    """Tests for plan tree API endpoint"""
    
    def test_get_plan_tree_success(self, db: Session, sample_plan: Plan):
        """Test successful retrieval of plan tree"""
        response = client.get(f"/api/plans/{sample_plan.id}/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "nodes" in data
        assert "root_nodes" in data
        assert "total_steps" in data
        assert "total_levels" in data
        assert "plan_id" in data
        assert "plan_version" in data
        
        assert data["total_steps"] == 4
        assert data["plan_id"] == str(sample_plan.id)
        assert data["plan_version"] == 1
        assert len(data["root_nodes"]) == 1
        assert data["root_nodes"][0]["step_id"] == "step_1"
    
    def test_get_plan_tree_not_found(self):
        """Test plan tree endpoint with non-existent plan"""
        fake_id = uuid4()
        response = client.get(f"/api/plans/{fake_id}/tree")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_plan_tree_with_metadata(self, db: Session, sample_plan: Plan):
        """Test plan tree with metadata included"""
        response = client.get(
            f"/api/plans/{sample_plan.id}/tree",
            params={"include_metadata": "true"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that root node has metadata
        root = data["root_nodes"][0]
        assert "step_id" in root
        assert "description" in root
        assert "type" in root
    
    def test_get_plan_tree_without_metadata(self, db: Session, sample_plan: Plan):
        """Test plan tree without metadata"""
        response = client.get(
            f"/api/plans/{sample_plan.id}/tree",
            params={"include_metadata": "false"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Tree should still be returned
        assert "nodes" in data
        assert "root_nodes" in data
    
    def test_get_plan_tree_empty_steps(self, db: Session):
        """Test plan tree with plan that has no steps"""
        # Create task
        task = Task(
            id=uuid4(),
            description="Empty plan task",
            status=TaskStatus.APPROVED,
            created_by_role="planner"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        
        # Create plan with no steps
        plan = Plan(
            id=uuid4(),
            task_id=task.id,
            version=1,
            goal="Empty plan",
            steps=[],
            status="approved"
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
        
        response = client.get(f"/api/plans/{plan.id}/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_steps"] == 0
        assert len(data["nodes"]) == 0
        assert len(data["root_nodes"]) == 0
        assert data["has_hierarchy"] is False
    
    def test_get_plan_tree_hierarchy_structure(self, db: Session, sample_plan: Plan):
        """Test that tree hierarchy is correctly structured"""
        response = client.get(f"/api/plans/{sample_plan.id}/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check hierarchy
        root = data["root_nodes"][0]
        assert root["step_id"] == "step_1"
        assert len(root["children"]) == 2
        
        # Check levels
        assert data["total_levels"] == 3
        
        # Check that step_4 is at level 2
        def find_step(node, step_id):
            """Recursively find step in tree"""
            if node["step_id"] == step_id:
                return node
            for child in node.get("children", []):
                result = find_step(child, step_id)
                if result:
                    return result
            return None
        
        step_4 = find_step(root, "step_4")
        assert step_4 is not None
        assert step_4["level"] == 2
    
    def test_get_plan_tree_includes_plan_info(self, db: Session, sample_plan: Plan):
        """Test that tree response includes plan information"""
        response = client.get(f"/api/plans/{sample_plan.id}/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["plan_id"] == str(sample_plan.id)
        assert data["plan_version"] == sample_plan.version
        assert data["plan_status"] == sample_plan.status
        assert data["plan_goal"] == sample_plan.goal


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
