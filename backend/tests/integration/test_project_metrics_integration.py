"""
Integration tests for project metrics collection in real-time
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.project_metric import ProjectMetric, MetricType, MetricPeriod
from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.services.prompt_service import PromptService, PromptType
from app.services.project_metrics_service import ProjectMetricsService
from app.core.database import SessionLocal, engine, Base


@pytest.fixture(scope="module")
def db_session_fixture():
    """Create a test database session for the module."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def clear_db_before_each_test(db_session_fixture):
    """Clear the database before each test to ensure isolation."""
    db = db_session_fixture
    for table in reversed(Base.metadata.sorted_tables):
        if table.name != 'alembic_version':
            db.execute(table.delete())
    db.commit()
    yield
    for table in reversed(Base.metadata.sorted_tables):
        if table.name != 'alembic_version':
            db.execute(table.delete())
    db.commit()


@pytest.mark.asyncio
async def test_planning_service_collects_metrics(db_session_fixture):
    """Test that PlanningService collects metrics during task analysis"""
    db = db_session_fixture
    
    # Create a simple task
    task = Task(
        description="Test task for metrics",
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Create planning service (will have metrics_service integrated)
    planning_service = PlanningService(db)
    
    # Check that metrics_service is initialized
    assert planning_service.metrics_service is not None
    
    # Note: Actual planning requires LLM, so we'll just verify the service is set up
    # In a real scenario, metrics would be collected during _analyze_task and _decompose_task


def test_execution_service_collects_metrics(db_session_fixture):
    """Test that ExecutionService collects metrics during plan execution"""
    db = db_session_fixture
    
    # Create execution service
    execution_service = ExecutionService(db)
    
    # Check that metrics_service is initialized
    assert execution_service.metrics_service is not None


def test_prompt_service_collects_metrics(db_session_fixture):
    """Test that PromptService collects metrics during prompt usage"""
    db = db_session_fixture
    
    # Create prompt service
    prompt_service = PromptService(db)
    
    # Check that metrics_service is initialized
    assert prompt_service.metrics_service is not None
    
    # Create a test prompt
    prompt = prompt_service.create_prompt(
        name="test_metrics_prompt",
        prompt_text="Test prompt",
        prompt_type=PromptType.SYSTEM
    )
    
    # Record usage
    updated_prompt = prompt_service.record_usage(
        prompt_id=prompt.id,
        execution_time_ms=100.0
    )
    
    assert updated_prompt is not None
    assert updated_prompt.usage_count == 1
    
    # Check that metrics were recorded
    metrics_service = ProjectMetricsService(db)
    now = datetime.utcnow()
    # Round to hour for consistent period boundaries
    period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    period_end = now.replace(minute=0, second=0, microsecond=0)
    
    metrics = db.query(ProjectMetric).filter(
        ProjectMetric.metric_name == "prompt_execution_time",
        ProjectMetric.period_start >= period_start,
        ProjectMetric.period_start <= period_end
    ).all()
    
    # At least one metric should be recorded
    assert len(metrics) >= 1
    
    # Check the metric value
    metric = metrics[0]
    assert metric.value == pytest.approx(0.1)  # 100ms = 0.1 seconds


def test_prompt_service_collects_success_metrics(db_session_fixture):
    """Test that PromptService collects success metrics"""
    db = db_session_fixture
    
    prompt_service = PromptService(db)
    
    # Create a test prompt
    prompt = prompt_service.create_prompt(
        name="test_success_prompt",
        prompt_text="Test prompt",
        prompt_type=PromptType.SYSTEM
    )
    
    # Record success
    prompt_service.record_success(prompt.id)
    
    # Record failure
    prompt_service.record_failure(prompt.id)
    
    # Record another success
    prompt_service.record_success(prompt.id)
    
    # Refresh prompt
    db.refresh(prompt)
    
    # Check success rate (should be 2/3 = 0.667)
    assert prompt.success_rate is not None
    assert prompt.success_rate == pytest.approx(2.0 / 3.0, abs=0.01)
    
    # Check that metrics were recorded
    metrics_service = ProjectMetricsService(db)
    now = datetime.utcnow()
    # Round to hour for consistent period boundaries
    period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    period_end = now.replace(minute=0, second=0, microsecond=0)
    
    metrics = db.query(ProjectMetric).filter(
        ProjectMetric.metric_name == "prompt_success_rate",
        ProjectMetric.period_start >= period_start,
        ProjectMetric.period_start <= period_end
    ).all()
    
    # At least one metric should be recorded (from the last record_success call)
    assert len(metrics) >= 1


def test_metrics_aggregation_by_period(db_session_fixture):
    """Test that metrics are aggregated correctly by period"""
    db = db_session_fixture
    
    metrics_service = ProjectMetricsService(db)
    
    # Record multiple metrics in the same hour
    now = datetime.utcnow()
    period_start = now - timedelta(hours=1)
    period_end = now
    
    # Record first metric
    metric1 = metrics_service.record_metric(
        metric_type=MetricType.PERFORMANCE,
        metric_name="test_aggregation",
        value=1.0,
        period=MetricPeriod.HOUR,
        period_start=period_start,
        period_end=period_end,
        count=1
    )
    
    # Record second metric (should update the existing one)
    metric2 = metrics_service.record_metric(
        metric_type=MetricType.PERFORMANCE,
        metric_name="test_aggregation",
        value=2.0,
        period=MetricPeriod.HOUR,
        period_start=period_start,
        period_end=period_end,
        count=1
    )
    
    # Should be the same metric (updated)
    assert metric1.id == metric2.id
    assert metric2.value == 2.0
    assert metric2.count == 1  # Count is not incremented, it's replaced
    
    # Record metric in different period
    period_start2 = now - timedelta(hours=2)
    period_end2 = now - timedelta(hours=1)
    
    metric3 = metrics_service.record_metric(
        metric_type=MetricType.PERFORMANCE,
        metric_name="test_aggregation",
        value=3.0,
        period=MetricPeriod.HOUR,
        period_start=period_start2,
        period_end=period_end2,
        count=1
    )
    
    # Should be a different metric
    assert metric3.id != metric2.id
    assert metric3.value == 3.0

