"""
Integration tests for benchmark models
"""
import pytest
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType
from app.core.database import SessionLocal


def test_benchmark_task_integration():
    """Integration test for BenchmarkTask model with database"""
    db = SessionLocal()
    try:
        # Create a task
        task = BenchmarkTask(
            task_type=BenchmarkTaskType.CODE_GENERATION,
            category="python",
            name="integration_test_task",
            task_description="Write a function to reverse a string",
            expected_output="def reverse(s): return s[::-1]",
            evaluation_criteria={"correctness": 1.0, "efficiency": 0.8},
            difficulty="easy",
            tags=["python", "string"],
            task_metadata={"test": True}
        )
        
        db.add(task)
        db.commit()
        
        # Retrieve the task
        retrieved = db.query(BenchmarkTask).filter(BenchmarkTask.name == "integration_test_task").first()
        
        assert retrieved is not None
        assert retrieved.task_type == BenchmarkTaskType.CODE_GENERATION
        assert retrieved.category == "python"
        assert retrieved.name == "integration_test_task"
        assert retrieved.task_description == "Write a function to reverse a string"
        assert retrieved.expected_output == "def reverse(s): return s[::-1]"
        assert retrieved.evaluation_criteria == {"correctness": 1.0, "efficiency": 0.8}
        assert retrieved.difficulty == "easy"
        assert retrieved.tags == ["python", "string"]
        assert retrieved.task_metadata == {"test": True}
        
        # Test filtering by type
        code_gen_tasks = db.query(BenchmarkTask).filter(
            BenchmarkTask.task_type == BenchmarkTaskType.CODE_GENERATION
        ).all()
        assert len(code_gen_tasks) > 0
        
        # Clean up
        db.delete(retrieved)
        db.commit()
        
    finally:
        db.close()

