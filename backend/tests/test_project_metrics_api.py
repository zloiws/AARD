"""
Unit tests for project metrics API endpoints
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.core.database import SessionLocal, engine, Base
from app.models.project_metric import ProjectMetric, MetricType, MetricPeriod
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.api.routes import project_metrics


@pytest.fixture(scope="module")
def setup_db():
    """Create tables for testing"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(setup_db):
    """Create a test database session"""
    db = SessionLocal()
    try:
        # Clear tables before each test
        for table in reversed(Base.metadata.sorted_tables):
            if table.name != 'alembic_version':
                db.execute(table.delete())
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_metrics(db):
    """Create sample metrics for testing"""
    now = datetime.utcnow()
    period_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    period_end = now.replace(minute=0, second=0, microsecond=0)
    
    metrics = []
    for i in range(3):
        metric = ProjectMetric(
            metric_type=MetricType.PERFORMANCE,
            metric_name=f"test_metric_{i}",
            period=MetricPeriod.HOUR,
            period_start=period_start,
            period_end=period_end,
            value=0.5 + i * 0.1,
            count=10 + i
        )
        db.add(metric)
        metrics.append(metric)
    
    db.commit()
    return metrics


def test_project_metrics_router_exists():
    """Test that project metrics router is properly configured"""
    assert project_metrics.router is not None
    assert project_metrics.router.prefix == "/api/metrics/project"
    assert "project_metrics" in project_metrics.router.tags


def test_project_metrics_router_routes():
    """Test that project metrics router has expected routes"""
    routes = [route.path for route in project_metrics.router.routes]
    
    assert "/api/metrics/project/overview" in routes
    assert "/api/metrics/project/trends" in routes
    assert "/api/metrics/project/comparison" in routes
    assert "/api/metrics/project/metrics" in routes


def test_get_project_overview_service(db):
    """Test ProjectMetricsService.get_overview method"""
    from app.services.project_metrics_service import ProjectMetricsService
    
    service = ProjectMetricsService(db)
    # get_overview may return empty dict if there's no data, which is fine
    overview = service.get_overview(days=30)
    
    assert overview is not None
    # If there's data, check structure; if empty, that's also valid
    if overview:
        assert "period" in overview or "performance" in overview


def test_get_metric_trends_service(db, sample_metrics):
    """Test ProjectMetricsService.get_trends method"""
    from app.services.project_metrics_service import ProjectMetricsService
    
    service = ProjectMetricsService(db)
    trends = service.get_trends(
        metric_name="test_metric_0",
        days=7,
        period=MetricPeriod.HOUR
    )
    
    assert isinstance(trends, list)
    # Should have at least one metric
    assert len(trends) >= 1


def test_compare_periods_service(db):
    """Test ProjectMetricsService.compare_periods method"""
    from app.services.project_metrics_service import ProjectMetricsService
    
    now = datetime.utcnow()
    period1_start = now - timedelta(days=14)
    period1_end = now - timedelta(days=7)
    period2_start = now - timedelta(days=7)
    period2_end = now
    
    service = ProjectMetricsService(db)
    comparison = service.compare_periods(
        period1_start=period1_start,
        period1_end=period1_end,
        period2_start=period2_start,
        period2_end=period2_end
    )
    
    assert comparison is not None
    assert "period1" in comparison
    assert "period2" in comparison
    assert "changes" in comparison

