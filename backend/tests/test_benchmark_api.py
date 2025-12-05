"""
Tests for benchmark API endpoints
"""
import pytest
from uuid import uuid4

from app.core.database import SessionLocal
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType
from app.models.benchmark_result import BenchmarkResult
from app.api.routes import benchmarks


def test_benchmark_router_exists():
    """Test that benchmark router is properly configured"""
    assert benchmarks.router is not None
    assert benchmarks.router.prefix == "/api/benchmarks"
    assert "benchmarks" in benchmarks.router.tags


def test_benchmark_router_routes():
    """Test that benchmark router has expected routes"""
    routes = [route.path for route in benchmarks.router.routes]
    route_str = " ".join(routes)
    
    assert "/tasks/" in route_str
    assert "/run/" in route_str
    assert "/results/" in route_str
    assert "/comparison/" in route_str
    assert "/stats/" in route_str


def test_benchmark_service_integration(db):
    """Test that BenchmarkService works with database"""
    from app.services.benchmark_service import BenchmarkService
    
    service = BenchmarkService(db)
    
    # Test listing tasks
    tasks = service.list_tasks(limit=5)
    assert isinstance(tasks, list)
    
    # Test getting stats
    counts = service.get_task_count_by_type()
    assert isinstance(counts, dict)
    assert "code_generation" in counts


@pytest.fixture
def db():
    """Create a test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
