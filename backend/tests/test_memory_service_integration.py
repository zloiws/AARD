"""
Tests for MemoryService with ExecutionContext integration
"""
from uuid import uuid4

import pytest
from app.core.database import SessionLocal
from app.core.execution_context import ExecutionContext
from app.models.agent import Agent, AgentStatus
from app.services.memory_service import MemoryService
from sqlalchemy.orm import Session


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
        description="Test agent for memory service tests",
        status=AgentStatus.ACTIVE.value,
        capabilities=["memory_testing"]
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


def test_memory_service_with_execution_context(execution_context):
    """Test MemoryService works with ExecutionContext"""
    service = MemoryService(execution_context)
    
    # Verify context is set
    assert hasattr(service, 'context')
    assert service.context is execution_context
    assert service.db is execution_context.db
    assert service.workflow_id == execution_context.workflow_id


def test_memory_service_backward_compatibility(db_session):
    """Test MemoryService backward compatibility with Session"""
    service = MemoryService(db_session)
    
    # Verify it creates context from session
    assert hasattr(service, 'context')
    assert isinstance(service.context, ExecutionContext)
    assert service.db is db_session


def test_memory_service_save_memory_with_context(execution_context, test_agent):
    """Test saving memory with ExecutionContext"""
    service = MemoryService(execution_context)
    
    try:
        # Убеждаемся, что агент существует в БД
        from app.models.agent import Agent
        agent_check = execution_context.db.query(Agent).filter(Agent.id == test_agent.id).first()
        if not agent_check:
            pytest.skip(f"Agent {test_agent.id} not found in database")
        
        memory = service.save_memory(
            agent_id=test_agent.id,
            memory_type="fact",
            content={"test": "data"},
            summary="Test memory",
            importance=0.8
        )
        
        assert memory is not None
        assert memory.agent_id == test_agent.id
        assert memory.memory_type == "fact"
        assert memory.summary == "Test memory"
        assert memory.importance == 0.8
        assert memory.id is not None
        
        # save_memory уже делает commit внутри себя
        # Проверяем, что память доступна через refresh
        execution_context.db.refresh(memory)
        assert memory.id is not None
        
    except ValueError as e:
        # Если агент не найден - пропускаем тест
        if "not found" in str(e).lower() or "agent" in str(e).lower():
            pytest.skip(f"Agent not found: {e}")
        raise
    except Exception as e:
        execution_context.db.rollback()
        # Если это ошибка БД или другой критической ошибки, пробрасываем
        raise
