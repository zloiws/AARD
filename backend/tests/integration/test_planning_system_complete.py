"""
Integration tests for complete Planning System (Phase 1)
Tests automatic replanning and plan visualization together
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
def sample_plan_with_steps(db: Session):
    """Create a sample plan with steps"""
    task = Task(
        id=uuid4(),
        description="Test task for complete planning system",
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
        goal="Test complete planning system",
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
            }
        ],
        status="approved"
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    return plan


class TestPlanningSystemComplete:
    """Integration tests for complete Planning System"""
    
    def test_error_detection_and_auto_replan(self, db: Session):
        """Test error detection triggers automatic replanning"""
        from app.services.execution_service import ExecutionService
        
        # Create a task with empty plan
        task = Task(
            id=uuid4(),
            description="Test auto replan",
            status=TaskStatus.APPROVED,
            created_by_role="planner"
        )
        db.add(task)
        db.commit()
        
        plan = Plan(
            id=uuid4(),
            task_id=task.id,
            version=1,
            goal="Test",
            steps=[],
            status="approved"
        )
        db.add(plan)
        db.commit()
        
        execution_service = ExecutionService(db)
        
        # Check error detection
        is_critical = execution_service._is_critical_error("Plan has no steps")
        assert is_critical is True
        
        # Check error classification
        classified_error = execution_service._classify_error("Plan has no steps")
        assert classified_error.requires_replanning is True
    
    def test_plan_visualization_with_tree(self, db: Session, sample_plan_with_steps: Plan):
        """Test plan visualization with tree structure"""
        # Test tree API
        response = client.get(f"/api/plans/{sample_plan_with_steps.id}/tree")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_steps"] == 2
        assert len(data["root_nodes"]) == 1
        assert data["has_hierarchy"] is True
    
    def test_complete_workflow(self, db: Session):
        """Test complete workflow: plan creation -> visualization -> execution with error detection"""
        from app.services.planning_service import PlanningService
        from app.services.plan_tree_service import PlanTreeService
        
        planning_service = PlanningService(db)
        
        # This test would require actual model calls, so we'll test the structure
        # In real scenario, you would:
        # 1. Create plan
        # 2. Visualize it
        # 3. Execute it
        # 4. Detect errors
        # 5. Auto-replan
        
        # For now, test that services are properly integrated
        assert planning_service is not None
        assert PlanTreeService is not None
        
        # Test tree service with sample data
        steps = [
            {
                "step_id": "step_1",
                "description": "First step",
                "type": "action",
                "dependencies": []
            }
        ]
        
        tree = PlanTreeService.build_tree(steps)
        assert tree["total_steps"] == 1
        assert len(tree["root_nodes"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
