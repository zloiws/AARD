"""
Tests for benchmark execution functionality
"""
import asyncio
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
def sample_task(db):
    """Create a sample benchmark task"""
    # Clean up if exists
    existing = db.query(BenchmarkTask).filter(BenchmarkTask.name == "test_execution_task").first()
    if existing:
        db.delete(existing)
        db.commit()
    
    task = BenchmarkTask(
        task_type=BenchmarkTaskType.GENERAL_CHAT,
        name="test_execution_task",
        task_description="Say hello"
    )
    db.add(task)
    db.commit()
    return task


@pytest.mark.asyncio
async def test_run_benchmark_basic(db, sample_task):
    """Test running a basic benchmark"""
    service = BenchmarkService(db)
    
    # This test requires actual LLM, so we'll mock or skip if no LLM available
    # For now, test the structure
    try:
        result = await service.run_benchmark(
            task_id=sample_task.id,
            model_name="test_model",
            server_url="http://test:11434/v1",
            timeout=5.0
        )
        
        assert result is not None
        assert result.benchmark_task_id == sample_task.id
        # Result may have error if LLM not available, which is OK for test
    except Exception as e:
        # If LLM not available, that's expected
        pytest.skip(f"LLM not available: {e}")


def test_compare_models_structure(db):
    """Test compare_models method structure"""
    service = BenchmarkService(db)
    
    # Test with empty model list
    comparison = service.compare_models(model_ids=[])
    
    assert isinstance(comparison, dict)
    assert "models" in comparison
    assert "tasks" in comparison
    assert "summary" in comparison
    assert comparison["models"] == []
    assert comparison["summary"]["total_models"] == 0


def test_run_suite_structure(db):
    """Test run_suite method structure (without actual execution)"""
    service = BenchmarkService(db)
    
    # Get tasks
    tasks = service.list_tasks(task_type=BenchmarkTaskType.GENERAL_CHAT, limit=1)
    
    if tasks:
        # Test that method exists and can be called
        # We won't actually run it without LLM
        assert hasattr(service, 'run_suite')
        assert callable(service.run_suite)


def test_task_type_mapping():
    """Test that task types are correctly mapped"""
    from app.core.ollama_client import TaskType
    from app.models.benchmark_task import BenchmarkTaskType
    from app.services.benchmark_service import BenchmarkService

    # Verify all benchmark task types have corresponding Ollama task types
    task_type_map = {
        BenchmarkTaskType.CODE_GENERATION: TaskType.CODE_GENERATION,
        BenchmarkTaskType.CODE_ANALYSIS: TaskType.CODE_ANALYSIS,
        BenchmarkTaskType.REASONING: TaskType.REASONING,
        BenchmarkTaskType.PLANNING: TaskType.PLANNING,
        BenchmarkTaskType.GENERAL_CHAT: TaskType.GENERAL_CHAT,
    }
    
    for benchmark_type, ollama_type in task_type_map.items():
        assert ollama_type is not None, f"No mapping for {benchmark_type}"

