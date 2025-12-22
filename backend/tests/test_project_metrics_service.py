"""
Unit tests for ProjectMetricsService
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from app.core.database import Base, SessionLocal, engine
from app.models.plan import Plan, PlanStatus
from app.models.project_metric import MetricPeriod, MetricType, ProjectMetric
from app.models.task import Task, TaskStatus
from app.models.trace import ExecutionTrace
from app.services.project_metrics_service import ProjectMetricsService


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


@pytest.fixture
def metrics_service(db_session_fixture):
    """Fixture for ProjectMetricsService"""
    return ProjectMetricsService(db_session_fixture)


def test_record_metric(metrics_service):
    """Test recording a metric"""
    period_start = datetime.utcnow()
    period_end = period_start + timedelta(hours=1)
    
    metric = metrics_service.record_metric(
        metric_type=MetricType.PERFORMANCE,
        metric_name="test_metric",
        value=0.85,
        period=MetricPeriod.HOUR,
        period_start=period_start,
        period_end=period_end,
        count=10
    )
    
    assert metric is not None
    assert metric.metric_type == MetricType.PERFORMANCE
    assert metric.metric_name == "test_metric"
    assert metric.value == 0.85
    assert metric.count == 10
    assert metric.period == MetricPeriod.HOUR


def test_record_metric_update_existing(metrics_service):
    """Test updating an existing metric"""
    period_start = datetime.utcnow()
    period_end = period_start + timedelta(hours=1)
    
    # Create initial metric
    metric1 = metrics_service.record_metric(
        metric_type=MetricType.PERFORMANCE,
        metric_name="test_metric",
        value=0.85,
        period=MetricPeriod.HOUR,
        period_start=period_start,
        period_end=period_end,
        count=10
    )
    
    # Update the same metric
    metric2 = metrics_service.record_metric(
        metric_type=MetricType.PERFORMANCE,
        metric_name="test_metric",
        value=0.90,
        period=MetricPeriod.HOUR,
        period_start=period_start,
        period_end=period_end,
        count=15
    )
    
    assert metric1.id == metric2.id
    assert metric2.value == 0.90
    assert metric2.count == 15


def test_collect_performance_metrics(metrics_service, db_session_fixture):
    """Test collecting performance metrics"""
    db = db_session_fixture
    
    # Create test tasks
    task1 = Task(
        description="Test task 1",
        status=TaskStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    task2 = Task(
        description="Test task 2",
        status=TaskStatus.FAILED,
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    task3 = Task(
        description="Test task 3",
        status=TaskStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    
    db.add_all([task1, task2, task3])
    db.commit()
    
    # Create execution traces
    now = datetime.utcnow() - timedelta(hours=1)
    trace1 = ExecutionTrace(
        trace_id=str(uuid4()),
        task_id=task1.id,
        operation_name="test_operation",
        status="success",
        duration_ms=1000,
        start_time=now,
        created_at=now
    )
    trace2 = ExecutionTrace(
        trace_id=str(uuid4()),
        task_id=task2.id,
        operation_name="test_operation",
        status="error",
        duration_ms=500,
        start_time=now,
        created_at=now
    )
    trace3 = ExecutionTrace(
        trace_id=str(uuid4()),
        task_id=task3.id,
        operation_name="test_operation",
        status="success",
        duration_ms=2000,
        start_time=now,
        created_at=now
    )
    
    db.add_all([trace1, trace2, trace3])
    db.commit()
    
    # Collect metrics
    period_start = datetime.utcnow() - timedelta(hours=2)
    period_end = datetime.utcnow()
    
    metrics = metrics_service.collect_performance_metrics(period_start, period_end)
    
    assert metrics["total_tasks"] == 3
    assert metrics["completed_tasks"] == 2
    assert metrics["failed_tasks"] == 1
    assert metrics["success_rate"] == pytest.approx(2.0 / 3.0)
    assert metrics["avg_execution_time"] == pytest.approx((1.0 + 0.5 + 2.0) / 3.0)


def test_collect_task_distribution(metrics_service, db_session_fixture):
    """Test collecting task distribution metrics"""
    db = db_session_fixture
    
    # Create test tasks with different statuses
    tasks = [
        Task(description=f"Task {i}", status=TaskStatus.COMPLETED, priority=5, autonomy_level=2,
             created_at=datetime.utcnow() - timedelta(hours=1))
        for i in range(3)
    ]
    tasks.append(
        Task(description="Failed task", status=TaskStatus.FAILED, priority=7, autonomy_level=3,
             created_at=datetime.utcnow() - timedelta(hours=1))
    )
    
    db.add_all(tasks)
    db.commit()
    
    period_start = datetime.utcnow() - timedelta(hours=2)
    period_end = datetime.utcnow()
    
    distribution = metrics_service.collect_task_distribution(period_start, period_end)
    
    assert distribution["total_tasks"] == 4
    assert distribution["status_distribution"][TaskStatus.COMPLETED.value] == 3
    assert distribution["status_distribution"][TaskStatus.FAILED.value] == 1
    assert distribution["priority_distribution"][5] == 3
    assert distribution["priority_distribution"][7] == 1


def test_get_overview(metrics_service, db_session_fixture):
    """Test getting overview metrics"""
    db = db_session_fixture
    
    # Create test data
    task = Task(
        description="Test task",
        status=TaskStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(days=1)
    )
    db.add(task)
    db.commit()
    
    plan = Plan(
        task_id=task.id,
        goal="Test goal",
        steps=[],
        status=PlanStatus.COMPLETED.value,
        created_at=datetime.utcnow() - timedelta(days=1)
    )
    db.add(plan)
    db.commit()
    
    overview = metrics_service.get_overview(days=30)
    
    assert "period" in overview
    assert "performance" in overview
    assert "distribution" in overview
    assert "plans" in overview
    assert overview["plans"]["total"] >= 1


def test_get_trends(metrics_service):
    """Test getting trends for a metric"""
    period_start = datetime.utcnow() - timedelta(days=5)
    period_end = datetime.utcnow()
    
    # Create some metrics
    for i in range(5):
        metrics_service.record_metric(
            metric_type=MetricType.PERFORMANCE,
            metric_name="test_trend",
            value=0.8 + i * 0.01,
            period=MetricPeriod.DAY,
            period_start=period_start + timedelta(days=i),
            period_end=period_start + timedelta(days=i+1),
            count=10
        )
    
    trends = metrics_service.get_trends("test_trend", days=7, period=MetricPeriod.DAY)
    
    assert len(trends) == 5
    assert all(t["metric_name"] == "test_trend" for t in trends)


def test_compare_periods(metrics_service, db_session_fixture):
    """Test comparing metrics between two periods"""
    db = db_session_fixture
    
    # Create tasks in period 1
    period1_start = datetime.utcnow() - timedelta(days=10)
    period1_end = datetime.utcnow() - timedelta(days=5)
    
    task1 = Task(
        description="Period 1 task",
        status=TaskStatus.COMPLETED,
        created_at=period1_start + timedelta(days=1)
    )
    db.add(task1)
    db.commit()
    
    trace1_time = period1_start + timedelta(days=1)
    trace1 = ExecutionTrace(
        trace_id=str(uuid4()),
        task_id=task1.id,
        operation_name="test_operation",
        status="success",
        duration_ms=1000,
        start_time=trace1_time,
        created_at=trace1_time
    )
    db.add(trace1)
    db.commit()
    
    # Create tasks in period 2
    period2_start = datetime.utcnow() - timedelta(days=5)
    period2_end = datetime.utcnow()
    
    task2 = Task(
        description="Period 2 task",
        status=TaskStatus.COMPLETED,
        created_at=period2_start + timedelta(days=1)
    )
    task3 = Task(
        description="Period 2 task 2",
        status=TaskStatus.COMPLETED,
        created_at=period2_start + timedelta(days=1)
    )
    db.add_all([task2, task3])
    db.commit()
    
    trace2_time = period2_start + timedelta(days=1)
    trace2 = ExecutionTrace(
        trace_id=str(uuid4()),
        task_id=task2.id,
        operation_name="test_operation",
        status="success",
        duration_ms=2000,
        start_time=trace2_time,
        created_at=trace2_time
    )
    trace3 = ExecutionTrace(
        trace_id=str(uuid4()),
        task_id=task3.id,
        operation_name="test_operation",
        status="success",
        duration_ms=1500,
        start_time=trace2_time,
        created_at=trace2_time
    )
    db.add_all([trace2, trace3])
    db.commit()
    
    comparison = metrics_service.compare_periods(
        period1_start, period1_end,
        period2_start, period2_end
    )
    
    assert "period1" in comparison
    assert "period2" in comparison
    assert "changes" in comparison
    assert comparison["period1"]["metrics"]["total_tasks"] == 1
    assert comparison["period2"]["metrics"]["total_tasks"] == 2

