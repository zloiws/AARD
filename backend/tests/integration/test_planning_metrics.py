"""
Integration tests for PlanningMetricsService
"""
import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session

from app.services.planning_metrics_service import PlanningMetricsService
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.models.trace import ExecutionTrace


@pytest.fixture
def test_task(db: Session) -> Task:
    """Create a test task"""
    task = Task(
        id=uuid4(),
        description="Test task",
        status=TaskStatus.PENDING.value,
        priority=5
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    yield task
    db.delete(task)
    db.commit()


@pytest.fixture
def test_plan(db: Session, test_task: Task) -> Plan:
    """Create a test plan"""
    plan = Plan(
        id=uuid4(),
        task_id=test_task.id,
        version=1,
        goal="Test plan goal",
        steps=[
            {
                "step_id": "step_1",
                "description": "Step 1",
                "type": "action"
            },
            {
                "step_id": "step_2",
                "description": "Step 2",
                "type": "action"
            }
        ],
        status=PlanStatus.DRAFT.value,
        estimated_duration=100
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    yield plan
    db.delete(plan)
    db.commit()


def test_calculate_plan_quality_score(db: Session, test_plan: Plan):
    """Test calculating plan quality score"""
    service = PlanningMetricsService(db)
    
    score = service.calculate_plan_quality_score(test_plan)
    
    assert 0.0 <= score <= 1.0
    assert score > 0.0  # Should have some score


def test_calculate_plan_quality_score_optimal_steps(db: Session, test_task: Task):
    """Test quality score for plan with optimal step count"""
    plan = Plan(
        id=uuid4(),
        task_id=test_task.id,
        version=1,
        goal="Test plan",
        steps=[
            {"step_id": f"step_{i}", "description": f"Step {i}", "type": "action"}
            for i in range(5)  # Optimal: 5 steps
        ],
        status=PlanStatus.DRAFT.value
    )
    db.add(plan)
    db.commit()
    
    try:
        service = PlanningMetricsService(db)
        score = service.calculate_plan_quality_score(plan)
        
        # Should have good score for optimal step count
        assert score >= 0.3  # At least step_count_score
    finally:
        db.delete(plan)
        db.commit()


def test_track_plan_execution_success(db: Session, test_plan: Plan):
    """Test tracking plan execution success"""
    service = PlanningMetricsService(db)
    
    service.track_plan_execution_success(
        plan_id=test_plan.id,
        success=True,
        execution_time_ms=5000
    )
    
    db.refresh(test_plan)
    assert test_plan.status == PlanStatus.COMPLETED.value
    assert test_plan.actual_duration == 5  # 5000ms = 5 seconds


def test_track_plan_execution_failure(db: Session, test_plan: Plan):
    """Test tracking plan execution failure"""
    service = PlanningMetricsService(db)
    
    service.track_plan_execution_success(
        plan_id=test_plan.id,
        success=False
    )
    
    db.refresh(test_plan)
    assert test_plan.status == PlanStatus.FAILED.value


def test_get_planning_statistics(db: Session, test_plan: Plan):
    """Test getting planning statistics"""
    service = PlanningMetricsService(db)
    
    stats = service.get_planning_statistics(time_range_days=30)
    
    assert "total_plans" in stats
    assert "completed" in stats
    assert "failed" in stats
    assert "success_rate" in stats
    assert "average_quality_score" in stats
    assert "average_steps_per_plan" in stats


def test_get_plan_quality_breakdown(db: Session, test_plan: Plan):
    """Test getting plan quality breakdown"""
    service = PlanningMetricsService(db)
    
    breakdown = service.get_plan_quality_breakdown(test_plan.id)
    
    assert "plan_id" in breakdown
    assert "overall_quality_score" in breakdown
    assert "factors" in breakdown
    assert "execution_stats" in breakdown
    assert breakdown["overall_quality_score"] >= 0.0


def test_get_plan_quality_breakdown_with_execution(db: Session, test_plan: Plan):
    """Test quality breakdown with execution traces"""
    # Create execution trace
    trace = ExecutionTrace(
        id=uuid4(),
        trace_id=f"trace_{uuid4()}",
        plan_id=test_plan.id,
        operation_name="test_operation",
        start_time=datetime.utcnow(),
        status="success"
    )
    db.add(trace)
    db.commit()
    
    try:
        service = PlanningMetricsService(db)
        breakdown = service.get_plan_quality_breakdown(test_plan.id)
        
        assert breakdown["execution_stats"]["total_executions"] == 1
        assert breakdown["execution_stats"]["successful"] == 1
        assert breakdown["factors"]["execution_success_rate"] > 0.0
    finally:
        db.delete(trace)
        db.commit()

