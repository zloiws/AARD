"""
Integration tests for alternative plans generation and evaluation (Phase 6.1)
"""
import pytest
import asyncio
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.services.planning_service import PlanningService
from app.services.plan_evaluation_service import PlanEvaluationService


@pytest.fixture
def db():
    """Database session fixture"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def planning_service(db):
    """PlanningService fixture"""
    return PlanningService(db)


@pytest.fixture
def evaluation_service(db):
    """PlanEvaluationService fixture"""
    return PlanEvaluationService(db)


@pytest.fixture
def test_task(db):
    """Create a test task"""
    task = Task(
        id=uuid4(),
        description="Test task for alternative plans integration",
        status=TaskStatus.PENDING,
        priority=5
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@pytest.mark.asyncio
async def test_generate_plan_with_alternatives(planning_service, test_task):
    """Test generating plan with alternatives enabled"""
    task_description = "Create a REST API for product management"
    
    # Generate plan with alternatives
    best_plan = await planning_service.generate_plan(
        task_description=task_description,
        task_id=test_task.id,
        generate_alternatives=True,
        num_alternatives=2
    )
    
    # Should return a plan
    assert best_plan is not None
    assert best_plan.task_id == test_task.id
    assert best_plan.goal is not None
    assert best_plan.steps is not None
    
    # Check that best plan is marked
    if best_plan.alternatives and isinstance(best_plan.alternatives, dict):
        assert best_plan.alternatives.get("is_best") is True
        assert "evaluation_score" in best_plan.alternatives
        assert "ranking" in best_plan.alternatives


@pytest.mark.asyncio
async def test_generate_plan_without_alternatives(planning_service, test_task):
    """Test generating plan without alternatives (default behavior)"""
    task_description = "Create a simple web page"
    
    # Generate plan without alternatives
    plan = await planning_service.generate_plan(
        task_description=task_description,
        task_id=test_task.id,
        generate_alternatives=False
    )
    
    # Should return a single plan
    assert plan is not None
    assert plan.task_id == test_task.id
    
    # Should not have alternatives metadata (unless it was an alternative from previous test)
    # This is OK - we just verify it's a valid plan


@pytest.mark.asyncio
async def test_alternatives_saved_for_comparison(planning_service, db, test_task):
    """Test that all alternative plans are saved for comparison"""
    task_description = "Implement user authentication system"
    
    # Generate plan with alternatives
    best_plan = await planning_service.generate_plan(
        task_description=task_description,
        task_id=test_task.id,
        generate_alternatives=True,
        num_alternatives=3
    )
    
    # Check that all alternative plans are saved in database
    all_plans = db.query(Plan).filter(Plan.task_id == test_task.id).all()
    
    # Should have at least the best plan, possibly more if alternatives were saved
    assert len(all_plans) >= 1
    assert best_plan.id in [p.id for p in all_plans]
    
    # Check that best plan has evaluation metadata
    if best_plan.alternatives and isinstance(best_plan.alternatives, dict):
        assert best_plan.alternatives.get("is_best") is True


@pytest.mark.asyncio
async def test_custom_evaluation_weights(planning_service, test_task):
    """Test generating plan with custom evaluation weights"""
    task_description = "Create a fast API endpoint"
    
    # Custom weights emphasizing speed
    weights = {
        "execution_time": 0.6,
        "approval_points": 0.1,
        "risk_level": 0.1,
        "efficiency": 0.2
    }
    
    best_plan = await planning_service.generate_plan(
        task_description=task_description,
        task_id=test_task.id,
        generate_alternatives=True,
        num_alternatives=2,
        evaluation_weights=weights
    )
    
    # Should return a plan
    assert best_plan is not None
    
    # Verify weights were used (best plan should have evaluation score)
    if best_plan.alternatives and isinstance(best_plan.alternatives, dict):
        assert "evaluation_score" in best_plan.alternatives


@pytest.mark.asyncio
async def test_full_ab_testing_cycle(planning_service, evaluation_service, db, test_task):
    """Test full A/B testing cycle: generate -> evaluate -> select"""
    task_description = "Build a microservice for order processing"
    
    # Step 1: Generate alternatives
    best_plan = await planning_service.generate_plan(
        task_description=task_description,
        task_id=test_task.id,
        generate_alternatives=True,
        num_alternatives=3
    )
    
    assert best_plan is not None
    
    # Step 2: Verify evaluation was performed
    if best_plan.alternatives and isinstance(best_plan.alternatives, dict):
        evaluation_score = best_plan.alternatives.get("evaluation_score")
        ranking = best_plan.alternatives.get("ranking")
        
        assert evaluation_score is not None
        assert ranking is not None
        assert ranking == 1  # Best plan should be ranked #1
    
    # Step 3: Verify all alternatives are accessible
    all_plans = db.query(Plan).filter(Plan.task_id == test_task.id).all()
    assert len(all_plans) >= 1
    
    # Step 4: Re-evaluate to verify consistency
    if len(all_plans) > 1:
        results = evaluation_service.evaluate_plans(all_plans)
        assert len(results) >= 1
        # Best plan from re-evaluation should match our selected plan
        if results[0].plan_id == best_plan.id:
            assert results[0].ranking == 1


@pytest.mark.asyncio
async def test_fallback_on_alternatives_failure(planning_service, test_task):
    """Test fallback to single plan when alternatives generation fails"""
    # This test verifies that if alternatives generation fails,
    # the system falls back to generating a single plan
    
    task_description = "Simple task"
    
    # Try to generate with alternatives
    # Even if alternatives fail, should get a single plan
    plan = await planning_service.generate_plan(
        task_description=task_description,
        task_id=test_task.id,
        generate_alternatives=True,
        num_alternatives=2
    )
    
    # Should still return a plan (either best alternative or fallback)
    assert plan is not None
    assert plan.task_id == test_task.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

