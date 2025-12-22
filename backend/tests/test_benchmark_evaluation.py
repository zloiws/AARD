"""
Tests for benchmark evaluation functionality
"""
from uuid import uuid4

import pytest
from app.core.database import SessionLocal
from app.models.benchmark_result import BenchmarkResult
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType
from app.services.benchmark_service import BenchmarkService


@pytest.fixture
def db():
    """Create a test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_task_with_expected(db):
    """Create a sample task with expected output"""
    existing = db.query(BenchmarkTask).filter(BenchmarkTask.name == "test_eval_task").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    task = BenchmarkTask(
        task_type=BenchmarkTaskType.CODE_GENERATION,
        name="test_eval_task",
        task_description="Write a function to add two numbers",
        expected_output="def add(a, b):\n    return a + b",
        evaluation_criteria={"correctness": 1.0, "code_quality": 0.8}
    )
    db.add(task)
    db.commit()
    return task


def test_simple_evaluate_exact_match(db, sample_task_with_expected):
    """Test simple evaluation with exact match"""
    service = BenchmarkService(db)
    
    result = BenchmarkResult(
        benchmark_task_id=sample_task_with_expected.id,
        output="def add(a, b):\n    return a + b",
        execution_time=1.0
    )
    db.add(result)
    db.commit()
    
    # Evaluate
    updated_result = service._simple_evaluate(
        result.output,
        sample_task_with_expected.expected_output,
        sample_task_with_expected.evaluation_criteria or {}
    )
    
    score, metrics = updated_result
    assert score == 1.0
    assert metrics.get("exact_match") is True


def test_simple_evaluate_contains_expected(db, sample_task_with_expected):
    """Test simple evaluation when output contains expected"""
    service = BenchmarkService(db)
    
    output = "Here's the function:\ndef add(a, b):\n    return a + b\nThat's it!"
    
    score, metrics = service._simple_evaluate(
        output,
        sample_task_with_expected.expected_output,
        {}
    )
    
    assert score >= 0.8
    assert metrics.get("contains_expected") is True


def test_simple_evaluate_no_match(db, sample_task_with_expected):
    """Test simple evaluation with no match"""
    service = BenchmarkService(db)
    
    output = "def subtract(a, b):\n    return a - b"
    
    score, metrics = service._simple_evaluate(
        output,
        sample_task_with_expected.expected_output,
        {}
    )
    
    assert score < 0.8
    assert "exact_match" not in metrics or metrics["exact_match"] is False


def test_simple_evaluate_no_expected_output(db, sample_task_with_expected):
    """Test simple evaluation when no expected output"""
    service = BenchmarkService(db)
    
    # Test with meaningful output (length > 10)
    score, metrics = service._simple_evaluate(
        "some meaningful output that is longer than 10 characters",
        None,
        {}
    )
    
    assert score == 0.6  # Increased from 0.5 for meaningful output
    assert metrics.get("no_expected_output") is True
    assert metrics.get("has_output") is True
    
    # Test with short/empty output
    score2, metrics2 = service._simple_evaluate(
        "short",
        None,
        {}
    )
    
    assert score2 == 0.3  # Lower score for poor output
    assert metrics2.get("no_expected_output") is True
    assert metrics2.get("has_output") is False


def test_calculate_score_from_metrics(db):
    """Test calculating score from metrics"""
    service = BenchmarkService(db)
    
    result = BenchmarkResult(
        benchmark_task_id=uuid4(),
        metrics={
            "correctness": 0.9,
            "code_quality": 0.8,
            "efficiency": 0.7
        }
    )
    
    score = service.calculate_score(result)
    
    # Should be average of metrics
    assert score == pytest.approx((0.9 + 0.8 + 0.7) / 3, rel=0.01)


def test_calculate_score_with_weights(db):
    """Test calculating score with weighted metrics"""
    service = BenchmarkService(db)
    
    result = BenchmarkResult(
        benchmark_task_id=uuid4(),
        metrics={
            "correctness": 0.9,
            "code_quality": 0.8
        }
    )
    
    criteria = {
        "weights": {
            "correctness": 0.7,
            "code_quality": 0.3
        }
    }
    
    score = service.calculate_score(result, criteria)
    
    # Weighted: 0.9 * 0.7 + 0.8 * 0.3 = 0.63 + 0.24 = 0.87
    assert score == pytest.approx(0.87, rel=0.01)


@pytest.mark.asyncio
async def test_evaluate_result_no_output(db, sample_task_with_expected):
    """Test evaluating result with no output (error)"""
    service = BenchmarkService(db)
    
    result = BenchmarkResult(
        benchmark_task_id=sample_task_with_expected.id,
        output=None,
        error_message="Timeout",
        execution_time=60.0
    )
    db.add(result)
    db.commit()
    
    # Evaluate
    updated = await service.evaluate_result(result.id, use_llm=False)
    
    assert updated.passed is False
    assert updated.score == 0.0
    assert updated.metrics.get("error") is True


@pytest.mark.asyncio
async def test_evaluate_result_with_output(db, sample_task_with_expected):
    """Test evaluating result with output"""
    service = BenchmarkService(db)
    
    result = BenchmarkResult(
        benchmark_task_id=sample_task_with_expected.id,
        output="def add(a, b):\n    return a + b",
        execution_time=1.0
    )
    db.add(result)
    db.commit()
    
    # Evaluate (without LLM for speed)
    updated = await service.evaluate_result(result.id, use_llm=False)
    
    assert updated.score is not None
    assert updated.score > 0.0
    assert updated.metrics is not None

