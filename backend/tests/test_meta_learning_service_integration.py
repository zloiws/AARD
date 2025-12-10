"""
Tests for MetaLearningService with ExecutionContext integration
"""
import pytest
from sqlalchemy.orm import Session

from app.core.execution_context import ExecutionContext
from app.core.database import SessionLocal
from app.services.meta_learning_service import MetaLearningService


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def execution_context(db_session):
    """Create an ExecutionContext for testing"""
    return ExecutionContext.from_db_session(db_session)


@pytest.mark.asyncio
async def test_meta_learning_service_with_execution_context(execution_context):
    """Test MetaLearningService works with ExecutionContext"""
    service = MetaLearningService(execution_context)
    
    # Verify context is set
    assert hasattr(service, 'context')
    assert service.context == execution_context
    assert service.db == execution_context.db
    assert service.workflow_id == execution_context.workflow_id


@pytest.mark.asyncio
async def test_meta_learning_service_backward_compatibility(db_session):
    """Test MetaLearningService backward compatibility with Session"""
    service = MetaLearningService(db_session)
    
    # Verify it creates context from session
    assert hasattr(service, 'context')
    assert isinstance(service.context, ExecutionContext)
    assert service.db == db_session


@pytest.mark.asyncio
async def test_meta_learning_service_analyze_patterns_with_context(execution_context):
    """Test analyze_execution_patterns with ExecutionContext"""
    service = MetaLearningService(execution_context)
    
    # This should work even with empty database
    result = service.analyze_execution_patterns(time_range_days=30)
    
    assert result is not None
    assert isinstance(result, dict)
    assert "total_executions" in result
    assert "successful" in result
    assert "failed" in result
    assert "overall_success_rate" in result
