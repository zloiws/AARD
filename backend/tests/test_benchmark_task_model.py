"""
Tests for BenchmarkTask model
"""
from datetime import datetime
from uuid import uuid4

import pytest
from app.core.database import Base, SessionLocal, engine
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType


@pytest.fixture
def db():
    """Create a test database session"""
    # Use existing database, don't drop tables
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_create_benchmark_task(db):
    """Test creating a benchmark task"""
    # Clean up if exists
    existing = db.query(BenchmarkTask).filter(BenchmarkTask.name == "test_task_1").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    task = BenchmarkTask(
        task_type=BenchmarkTaskType.CODE_GENERATION,
        category="python",
        name="test_task_1",
        task_description="Write a function to calculate factorial",
        expected_output="def factorial(n): ...",
        evaluation_criteria={"accuracy": 1.0, "code_quality": 0.8},
        difficulty="medium",
        tags=["python", "recursion"],
        task_metadata={"source": "test"}
    )
    
    db.add(task)
    db.commit()
    
    assert task.id is not None
    assert task.task_type == BenchmarkTaskType.CODE_GENERATION
    assert task.category == "python"
    assert task.name == "test_task_1"
    assert task.task_description == "Write a function to calculate factorial"
    assert task.expected_output == "def factorial(n): ..."
    assert task.evaluation_criteria == {"accuracy": 1.0, "code_quality": 0.8}
    assert task.difficulty == "medium"
    assert task.tags == ["python", "recursion"]
    assert task.task_metadata == {"source": "test"}
    assert task.created_at is not None
    assert task.updated_at is not None


def test_benchmark_task_unique_name(db):
    """Test that task names must be unique"""
    # Clean up if exists
    existing = db.query(BenchmarkTask).filter(BenchmarkTask.name == "unique_task").all()
    for e in existing:
        db.delete(e)
    db.commit()
    
    task1 = BenchmarkTask(
        task_type=BenchmarkTaskType.CODE_GENERATION,
        name="unique_task",
        task_description="Test task"
    )
    db.add(task1)
    db.commit()
    
    task2 = BenchmarkTask(
        task_type=BenchmarkTaskType.CODE_ANALYSIS,
        name="unique_task",  # Same name
        task_description="Another test task"
    )
    db.add(task2)
    
    with pytest.raises(Exception):  # Should raise IntegrityError
        db.commit()


def test_benchmark_task_to_dict(db):
    """Test converting task to dictionary"""
    # Clean up if exists
    existing = db.query(BenchmarkTask).filter(BenchmarkTask.name == "math_task_1").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    task = BenchmarkTask(
        task_type=BenchmarkTaskType.REASONING,
        category="math",
        name="math_task_1",
        task_description="Solve: 2x + 5 = 15",
        expected_output="x = 5",
        evaluation_criteria={"correctness": 1.0},
        difficulty="easy",
        tags=["math", "algebra"]
    )
    
    db.add(task)
    db.commit()
    
    task_dict = task.to_dict()
    
    assert task_dict["id"] == str(task.id)
    assert task_dict["task_type"] == "reasoning"
    assert task_dict["category"] == "math"
    assert task_dict["name"] == "math_task_1"
    assert task_dict["task_description"] == "Solve: 2x + 5 = 15"
    assert task_dict["expected_output"] == "x = 5"
    assert task_dict["evaluation_criteria"] == {"correctness": 1.0}
    assert task_dict["difficulty"] == "easy"
    assert task_dict["tags"] == ["math", "algebra"]


def test_benchmark_task_types(db):
    """Test all benchmark task types"""
    types = [
        BenchmarkTaskType.CODE_GENERATION,
        BenchmarkTaskType.CODE_ANALYSIS,
        BenchmarkTaskType.REASONING,
        BenchmarkTaskType.PLANNING,
        BenchmarkTaskType.GENERAL_CHAT,
    ]
    
    # Clean up existing test tasks
    for task_type in types:
        existing = db.query(BenchmarkTask).filter(BenchmarkTask.name == f"test_{task_type.value}").first()
        if existing:
            db.delete(existing)
    db.commit()
    
    # Create new tasks
    created_tasks = []
    for task_type in types:
        task = BenchmarkTask(
            task_type=task_type,
            name=f"test_{task_type.value}",
            task_description=f"Test {task_type.value} task"
        )
        db.add(task)
        created_tasks.append(task)
    
    db.commit()
    
    # Verify each type exists
    for task_type in types:
        found = db.query(BenchmarkTask).filter(BenchmarkTask.task_type == task_type).first()
        assert found is not None
        assert found.task_type == task_type

