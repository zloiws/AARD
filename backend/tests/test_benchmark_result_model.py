"""
Tests for BenchmarkResult model
"""
import pytest
from datetime import datetime
from uuid import uuid4

from app.models.benchmark_result import BenchmarkResult
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType
from app.core.database import SessionLocal


@pytest.fixture
def db():
    """Create a test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_task(db):
    """Create a sample benchmark task"""
    # Clean up if exists
    existing = db.query(BenchmarkTask).filter(BenchmarkTask.name == "test_result_task").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    task = BenchmarkTask(
        task_type=BenchmarkTaskType.CODE_GENERATION,
        name="test_result_task",
        task_description="Test task for results"
    )
    db.add(task)
    db.commit()
    return task


def test_create_benchmark_result(db, sample_task):
    """Test creating a benchmark result"""
    result = BenchmarkResult(
        benchmark_task_id=sample_task.id,
        execution_time=1.5,
        output="def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
        score=0.95,
        metrics={"accuracy": 1.0, "code_quality": 0.9},
        passed=True,
        execution_metadata={"model": "test_model", "temperature": 0.7}
    )
    
    db.add(result)
    db.commit()
    
    assert result.id is not None
    assert result.benchmark_task_id == sample_task.id
    assert result.execution_time == 1.5
    assert result.output == "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)"
    assert result.score == 0.95
    assert result.metrics == {"accuracy": 1.0, "code_quality": 0.9}
    assert result.passed is True
    assert result.execution_metadata == {"model": "test_model", "temperature": 0.7}
    assert result.created_at is not None


def test_benchmark_result_failed(db, sample_task):
    """Test creating a failed benchmark result"""
    result = BenchmarkResult(
        benchmark_task_id=sample_task.id,
        execution_time=0.5,
        output=None,
        score=0.0,
        passed=False,
        error_message="Timeout error"
    )
    
    db.add(result)
    db.commit()
    
    assert result.passed is False
    assert result.score == 0.0
    assert result.error_message == "Timeout error"
    assert result.output is None


def test_benchmark_result_to_dict(db, sample_task):
    """Test converting result to dictionary"""
    result = BenchmarkResult(
        benchmark_task_id=sample_task.id,
        execution_time=2.0,
        output="test output",
        score=0.8,
        metrics={"test": "metric"},
        passed=True
    )
    
    db.add(result)
    db.commit()
    
    result_dict = result.to_dict()
    
    assert result_dict["id"] == str(result.id)
    assert result_dict["benchmark_task_id"] == str(sample_task.id)
    assert result_dict["execution_time"] == 2.0
    assert result_dict["output"] == "test output"
    assert result_dict["score"] == 0.8
    assert result_dict["metrics"] == {"test": "metric"}
    assert result_dict["passed"] is True


def test_benchmark_result_relationship(db, sample_task):
    """Test relationship with BenchmarkTask"""
    result = BenchmarkResult(
        benchmark_task_id=sample_task.id,
        execution_time=1.0,
        output="test",
        score=0.5,
        passed=False
    )
    
    db.add(result)
    db.commit()
    
    # Test relationship
    assert result.task is not None
    assert result.task.id == sample_task.id
    assert result.task.name == "test_result_task"
    
    # Test backref
    assert len(sample_task.results) > 0
    assert result in sample_task.results

