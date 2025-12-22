"""
Tests for BenchmarkService
"""
import json
import tempfile
from pathlib import Path

import pytest
from app.core.database import SessionLocal
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
def sample_task_data():
    """Sample task data for testing"""
    return {
        "name": "test_import_task",
        "task_type": "code_generation",
        "category": "python",
        "task_description": "Test task description",
        "expected_output": "Test output",
        "evaluation_criteria": {"correctness": 1.0},
        "difficulty": "easy",
        "tags": ["test"]
    }


def test_import_task(db, sample_task_data):
    """Test importing a single task"""
    service = BenchmarkService(db)
    
    # Clean up if exists
    existing = service.get_task_by_name("test_import_task")
    if existing:
        db.delete(existing)
        db.commit()
    
    # Import task
    task = service.import_task(sample_task_data)
    
    assert task is not None
    assert task.name == "test_import_task"
    assert task.task_type == BenchmarkTaskType.CODE_GENERATION
    assert task.category == "python"
    assert task.task_description == "Test task description"
    
    # Verify it's in database
    retrieved = service.get_task_by_name("test_import_task")
    assert retrieved is not None
    assert retrieved.id == task.id


def test_import_task_duplicate(db, sample_task_data):
    """Test that importing duplicate task doesn't create a new one"""
    service = BenchmarkService(db)
    
    # Clean up if exists
    existing = service.get_task_by_name("test_import_task")
    if existing:
        db.delete(existing)
        db.commit()
    
    # Import first time
    task1 = service.import_task(sample_task_data)
    
    # Import second time (should return existing)
    task2 = service.import_task(sample_task_data)
    
    assert task1.id == task2.id
    assert task1.name == task2.name


def test_load_tasks_from_file(db):
    """Test loading tasks from a JSON file"""
    service = BenchmarkService(db)
    
    # Create temporary JSON file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        tasks_data = [
            {
                "name": "temp_task_1",
                "task_type": "reasoning",
                "task_description": "Test task 1"
            },
            {
                "name": "temp_task_2",
                "task_type": "planning",
                "task_description": "Test task 2"
            }
        ]
        json.dump(tasks_data, f)
        temp_file = Path(f.name)
    
    try:
        tasks = service.load_tasks_from_file(temp_file)
        
        assert len(tasks) == 2
        assert tasks[0]['name'] == "temp_task_1"
        assert tasks[1]['name'] == "temp_task_2"
    finally:
        temp_file.unlink()


def test_list_tasks(db):
    """Test listing tasks with filters"""
    service = BenchmarkService(db)
    
    # List all tasks
    all_tasks = service.list_tasks()
    assert len(all_tasks) > 0
    
    # Filter by type
    code_gen_tasks = service.list_tasks(task_type=BenchmarkTaskType.CODE_GENERATION)
    assert all(task.task_type == BenchmarkTaskType.CODE_GENERATION for task in code_gen_tasks)
    
    # Filter by category
    python_tasks = service.list_tasks(category="python")
    assert all(task.category == "python" for task in python_tasks)
    
    # Filter by difficulty
    easy_tasks = service.list_tasks(difficulty="easy")
    assert all(task.difficulty == "easy" for task in easy_tasks)
    
    # Limit
    limited = service.list_tasks(limit=5)
    assert len(limited) <= 5


def test_get_task_count_by_type(db):
    """Test getting task counts by type"""
    service = BenchmarkService(db)
    
    counts = service.get_task_count_by_type()
    
    assert isinstance(counts, dict)
    assert "code_generation" in counts
    assert "code_analysis" in counts
    assert "reasoning" in counts
    assert "planning" in counts
    assert "general_chat" in counts
    
    # All counts should be non-negative
    assert all(count >= 0 for count in counts.values())


def test_import_tasks_from_directory(db):
    """Test importing tasks from a directory"""
    service = BenchmarkService(db)
    
    # Use the actual benchmarks directory
    benchmarks_dir = Path(__file__).parent.parent / "data" / "benchmarks"
    
    if benchmarks_dir.exists():
        # Count existing tasks
        initial_counts = service.get_task_count_by_type()
        initial_total = sum(initial_counts.values())
        
        # Import (should skip existing)
        stats = service.import_tasks_from_directory(benchmarks_dir)
        
        # Verify stats
        assert stats['total'] > 0
        assert stats['imported'] >= 0  # May be 0 if all already exist
        assert stats['errors'] == 0
        
        # Verify tasks exist
        final_counts = service.get_task_count_by_type()
        final_total = sum(final_counts.values())
        
        # Total should be at least initial (may be more if new tasks added)
        assert final_total >= initial_total

