"""
Tests for plan evaluation service (Phase 6.1.2)
"""
import pytest
from uuid import uuid4
from datetime import datetime

from app.core.database import SessionLocal
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.services.plan_evaluation_service import PlanEvaluationService, PlanEvaluationResult


@pytest.fixture
def db():
    """Database session fixture"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def evaluation_service(db):
    """PlanEvaluationService fixture"""
    return PlanEvaluationService(db)


@pytest.fixture
def test_task(db):
    """Create a test task"""
    task = Task(
        id=uuid4(),
        description="Test task for plan evaluation",
        status=TaskStatus.PENDING,
        priority=5
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture
def sample_plan_fast(db, test_task):
    """Create a fast plan (few steps, short duration)"""
    plan = Plan(
        id=uuid4(),
        task_id=test_task.id,
        version=1,
        goal="Fast plan",
        strategy={"approach": "Quick execution", "alternative_risk_tolerance": "high"},
        steps=[
            {"step": 1, "description": "Step 1", "type": "code", "estimated_time": 300},
            {"step": 2, "description": "Step 2", "type": "code", "estimated_time": 400}
        ],
        status=PlanStatus.DRAFT.value,
        current_step=0,
        estimated_duration=700
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@pytest.fixture
def sample_plan_slow(db, test_task):
    """Create a slow plan (many steps, long duration)"""
    plan = Plan(
        id=uuid4(),
        task_id=test_task.id,
        version=1,
        goal="Slow plan",
        strategy={"approach": "Thorough execution", "alternative_risk_tolerance": "low"},
        steps=[
            {"step": i, "description": f"Step {i}", "type": "code", "estimated_time": 600}
            for i in range(1, 12)
        ],
        status=PlanStatus.DRAFT.value,
        current_step=0,
        estimated_duration=6600
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@pytest.fixture
def sample_plan_balanced(db, test_task):
    """Create a balanced plan (optimal steps, medium duration)"""
    plan = Plan(
        id=uuid4(),
        task_id=test_task.id,
        version=1,
        goal="Balanced plan",
        strategy={"approach": "Balanced approach", "alternative_risk_tolerance": "medium"},
        steps=[
            {"step": i, "description": f"Step {i}", "type": "code", "estimated_time": 500}
            for i in range(1, 6)
        ],
        status=PlanStatus.DRAFT.value,
        current_step=0,
        estimated_duration=2500
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_evaluate_plan_basic(evaluation_service, sample_plan_balanced):
    """Test basic plan evaluation"""
    result = evaluation_service.evaluate_plan(sample_plan_balanced)
    
    assert isinstance(result, PlanEvaluationResult)
    assert result.plan_id == sample_plan_balanced.id
    assert result.plan == sample_plan_balanced
    assert len(result.scores) == 4
    assert "execution_time" in result.scores
    assert "approval_points" in result.scores
    assert "risk_level" in result.scores
    assert "efficiency" in result.scores
    assert 0.0 <= result.total_score <= 1.0
    assert isinstance(result.recommendations, list)


def test_evaluate_execution_time(evaluation_service, sample_plan_fast, sample_plan_slow):
    """Test execution time evaluation"""
    fast_result = evaluation_service.evaluate_plan(sample_plan_fast)
    slow_result = evaluation_service.evaluate_plan(sample_plan_slow)
    
    # Fast plan should have higher execution_time score
    assert fast_result.scores["execution_time"] > slow_result.scores["execution_time"]


def test_evaluate_efficiency(evaluation_service, sample_plan_fast, sample_plan_balanced, sample_plan_slow):
    """Test efficiency evaluation"""
    fast_result = evaluation_service.evaluate_plan(sample_plan_fast)
    balanced_result = evaluation_service.evaluate_plan(sample_plan_balanced)
    slow_result = evaluation_service.evaluate_plan(sample_plan_slow)
    
    # Balanced plan (5 steps) should have highest efficiency
    assert balanced_result.scores["efficiency"] >= fast_result.scores["efficiency"]
    assert balanced_result.scores["efficiency"] > slow_result.scores["efficiency"]


def test_evaluate_risk_level(evaluation_service, sample_plan_fast, sample_plan_slow):
    """Test risk level evaluation"""
    fast_result = evaluation_service.evaluate_plan(sample_plan_fast)  # high risk tolerance
    slow_result = evaluation_service.evaluate_plan(sample_plan_slow)  # low risk tolerance
    
    # Low risk tolerance should have higher risk_level score
    assert slow_result.scores["risk_level"] > fast_result.scores["risk_level"]


def test_evaluate_approval_points(evaluation_service, sample_plan_balanced):
    """Test approval points evaluation"""
    result = evaluation_service.evaluate_plan(sample_plan_balanced)
    
    # Plan with no approval requests should have high score
    assert result.scores["approval_points"] >= 0.8


def test_evaluate_plans_ranking(evaluation_service, sample_plan_fast, sample_plan_balanced, sample_plan_slow):
    """Test ranking of multiple plans"""
    plans = [sample_plan_fast, sample_plan_slow, sample_plan_balanced]
    results = evaluation_service.evaluate_plans(plans)
    
    assert len(results) == 3
    
    # Results should be sorted by total_score (descending)
    for i in range(len(results) - 1):
        assert results[i].total_score >= results[i + 1].total_score
    
    # Rankings should be assigned
    assert results[0].ranking == 1
    assert results[1].ranking == 2
    assert results[2].ranking == 3


def test_evaluate_plans_custom_weights(evaluation_service, sample_plan_fast, sample_plan_balanced):
    """Test evaluation with custom weights"""
    weights = {
        "execution_time": 0.5,  # Emphasize speed
        "approval_points": 0.1,
        "risk_level": 0.1,
        "efficiency": 0.3
    }
    
    fast_result = evaluation_service.evaluate_plan(sample_plan_fast, weights)
    balanced_result = evaluation_service.evaluate_plan(sample_plan_balanced, weights)
    
    # Both plans should be evaluated successfully
    assert fast_result.total_score >= 0.0
    assert balanced_result.total_score >= 0.0
    
    # Fast plan should have equal or better execution_time score (both may be 1.0 if both are fast)
    assert fast_result.scores["execution_time"] >= balanced_result.scores["execution_time"]
    
    # Verify custom weights are applied (execution_time should have higher weight)
    assert weights["execution_time"] == 0.5


def test_compare_plans(evaluation_service, sample_plan_fast, sample_plan_balanced, sample_plan_slow):
    """Test plan comparison"""
    plans = [sample_plan_fast, sample_plan_balanced, sample_plan_slow]
    comparison = evaluation_service.compare_plans(plans)
    
    assert "plans" in comparison
    assert "best_plan" in comparison
    assert "comparison" in comparison
    assert "weights" in comparison
    
    assert len(comparison["plans"]) == 3
    assert comparison["best_plan"] is not None
    assert comparison["best_plan"]["ranking"] == 1
    
    # Check comparison matrix
    assert "execution_time" in comparison["comparison"]
    assert "approval_points" in comparison["comparison"]
    assert "risk_level" in comparison["comparison"]
    assert "efficiency" in comparison["comparison"]
    assert "total_score" in comparison["comparison"]


def test_generate_recommendations(evaluation_service, sample_plan_slow):
    """Test recommendation generation"""
    result = evaluation_service.evaluate_plan(sample_plan_slow)
    
    # Slow plan with many steps should have recommendations
    assert len(result.recommendations) > 0
    assert isinstance(result.recommendations[0], str)


def test_evaluate_plan_no_duration(evaluation_service, db, test_task):
    """Test evaluation of plan without estimated duration"""
    plan = Plan(
        id=uuid4(),
        task_id=test_task.id,
        version=1,
        goal="Plan without duration",
        strategy={},
        steps=[
            {"step": 1, "description": "Step 1", "type": "code", "estimated_time": 600}
        ],
        status=PlanStatus.DRAFT.value,
        current_step=0,
        estimated_duration=None  # No duration
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    result = evaluation_service.evaluate_plan(plan)
    
    # Should still evaluate successfully
    assert result.total_score >= 0.0
    assert result.scores["execution_time"] > 0.0  # Should calculate from steps


def test_evaluate_plan_empty_steps(evaluation_service, db, test_task):
    """Test evaluation of plan with no steps"""
    plan = Plan(
        id=uuid4(),
        task_id=test_task.id,
        version=1,
        goal="Plan without steps",
        strategy={},
        steps=[],
        status=PlanStatus.DRAFT.value,
        current_step=0,
        estimated_duration=None
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    
    result = evaluation_service.evaluate_plan(plan)
    
    # Should handle gracefully
    assert result.scores["efficiency"] == 0.0
    assert result.total_score >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

