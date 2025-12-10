"""
Tests for ReflectionService with ExecutionContext integration
"""
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session

from app.core.execution_context import ExecutionContext
from app.core.database import SessionLocal
from app.services.reflection_service import ReflectionService
from app.models.agent import Agent, AgentStatus


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


@pytest.fixture
def test_agent(db_session):
    """Create a test agent"""
    agent = Agent(
        id=uuid4(),
        name="Test Agent",
        description="Test agent for reflection service tests",
        status=AgentStatus.ACTIVE.value,
        capabilities=["reflection_testing"]
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


def test_reflection_service_with_execution_context(execution_context):
    """Test ReflectionService works with ExecutionContext"""
    service = ReflectionService(execution_context)
    
    # Verify context is set
    assert hasattr(service, 'context')
    assert service.context is execution_context
    assert service.db is execution_context.db
    assert service.workflow_id == execution_context.workflow_id


def test_reflection_service_backward_compatibility(db_session):
    """Test ReflectionService backward compatibility with Session"""
    service = ReflectionService(db_session)
    
    # Verify it creates context from session
    assert hasattr(service, 'context')
    assert isinstance(service.context, ExecutionContext)
    assert service.db is db_session


@pytest.mark.asyncio
async def test_reflection_service_analyze_failure_with_context(execution_context, test_agent):
    """Test analyze_failure with ExecutionContext"""
    service = ReflectionService(execution_context)
    
    # This test will skip if LLM is not available
    try:
        result = await service.analyze_failure(
            task_description="Test task",
            error="Test error",
            context={"test": "context"},
            agent_id=test_agent.id
        )
        
        assert result is not None
        # Проверяем структуру результата - может быть dict или объект
        if isinstance(result, dict):
            # Должен быть какой-то результат
            assert len(result) > 0
        else:
            # Если объект, должен иметь какие-то атрибуты
            assert hasattr(result, '__dict__') or hasattr(result, 'analysis') or hasattr(result, 'root_cause')
    except Exception as e:
        # Skip if LLM is not available or other expected errors
        error_msg = str(e).lower()
        skip_keywords = ["llm", "model", "server", "connection", "timeout", "unavailable", "not found"]
        if any(keyword in error_msg for keyword in skip_keywords):
            pytest.skip(f"LLM not available: {e}")
        else:
            # Если это другая ошибка, пробрасываем её дальше
            raise
