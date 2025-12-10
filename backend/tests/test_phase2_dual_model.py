"""
Тесты для Этапа 2: Dual-Model архитектура
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from app.agents.planner_agent import PlannerAgent
from app.agents.coder_agent import CoderAgent
from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.core.execution_context import ExecutionContext
from app.core.function_calling import FunctionCallProtocol


@pytest.fixture
def db_session():
    """Создать тестовую сессию БД"""
    from app.core.database import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def execution_context(db_session):
    """Создать ExecutionContext для тестов"""
    context = ExecutionContext.from_db_session(db_session)
    context.workflow_id = str(uuid4())
    return context


class TestPlannerAgent:
    """Тесты для PlannerAgent"""
    
    def test_planner_agent_creation(self, db_session):
        """Проверить создание PlannerAgent"""
        from app.services.agent_service import AgentService
        
        agent_service = AgentService(db_session)
        
        # Создать тестового агента
        agent = agent_service.create_agent(
            name=f"TestPlannerAgent_{uuid4().hex[:8]}",
            description="Test Planner Agent",
            capabilities=["planning", "reasoning"],
            created_by="test"
        )
        
        # Установить статус напрямую для тестов (в реальной системе нужно пройти через waiting_approval)
        agent.status = "active"
        db_session.commit()
        db_session.refresh(agent)
        
        planner = PlannerAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db_session
        )
        
        assert planner is not None
        assert planner.agent_id == agent.id
    
    @pytest.mark.asyncio
    async def test_planner_agent_analyze_task(self, db_session):
        """Проверить метод analyze_task PlannerAgent"""
        from app.services.agent_service import AgentService
        
        agent_service = AgentService(db_session)
        agent = agent_service.create_agent(
            name=f"TestPlanner_{uuid4().hex[:8]}",
            description="Test",
            capabilities=["planning"],
            created_by="test"
        )
        
        # Установить статус напрямую для тестов (в реальной системе нужно пройти через waiting_approval)
        agent.status = "active"
        db_session.commit()
        db_session.refresh(agent)
        
        planner = PlannerAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db_session
        )
        
        # Тест с моком LLM
        with patch.object(planner, 'ollama_client') as mock_client:
            mock_response = Mock()
            mock_response.response = '{"goal": "test", "requirements": [], "constraints": []}'
            mock_client.generate = AsyncMock(return_value=mock_response)
            
            result = await planner.analyze_task(
                task_description="Test task",
                context={}
            )
            
            assert result is not None
            assert isinstance(result, dict)


class TestCoderAgent:
    """Тесты для CoderAgent"""
    
    def test_coder_agent_creation(self, db_session):
        """Проверить создание CoderAgent"""
        from app.services.agent_service import AgentService
        
        agent_service = AgentService(db_session)
        agent = agent_service.create_agent(
            name=f"TestCoderAgent_{uuid4().hex[:8]}",
            description="Test Coder Agent",
            capabilities=["code_generation"],
            created_by="test"
        )
        
        # Установить статус напрямую для тестов (в реальной системе нужно пройти через waiting_approval)
        agent.status = "active"
        db_session.commit()
        db_session.refresh(agent)
        
        coder = CoderAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db_session
        )
        
        assert coder is not None
        assert coder.agent_id == agent.id


class TestDualModelIntegration:
    """Тесты для интеграции dual-model архитектуры"""
    
    def test_planning_service_has_planner_agent(self, execution_context):
        """Проверить, что PlanningService имеет метод _get_planner_agent"""
        service = PlanningService(execution_context)
        assert hasattr(service, '_get_planner_agent')
        assert callable(service._get_planner_agent)
    
    def test_execution_service_has_coder_agent(self, execution_context):
        """Проверить, что ExecutionService имеет метод _get_coder_agent"""
        service = ExecutionService(execution_context)
        assert hasattr(service, '_get_coder_agent')
        assert callable(service._get_coder_agent)
    
    @pytest.mark.asyncio
    async def test_planner_agent_creates_function_call(self, db_session):
        """Проверить, что PlannerAgent создает FunctionCall"""
        from app.services.agent_service import AgentService
        
        agent_service = AgentService(db_session)
        agent = agent_service.create_agent(
            name=f"TestPlanner_{uuid4().hex[:8]}",
            description="Test",
            capabilities=["planning"],
            created_by="test"
        )
        
        # Установить статус напрямую для тестов (в реальной системе нужно пройти через waiting_approval)
        agent.status = "active"
        db_session.commit()
        db_session.refresh(agent)
        
        planner = PlannerAgent(
            agent_id=agent.id,
            agent_service=agent_service,
            db_session=db_session
        )
        
        step = {
            "step_id": "step_1",
            "description": "Test step",
            "type": "action"
        }
        
        function_call = await planner.create_code_prompt(
            step=step,
            plan_context={}
        )
        
        assert function_call is not None
        assert hasattr(function_call, 'function')
        assert hasattr(function_call, 'parameters')
    
    def test_function_call_protocol(self):
        """Проверить FunctionCallProtocol"""
        function_call = FunctionCallProtocol.create_function_call(
            function_name="code_execution_tool",
            parameters={"code": "print('test')", "language": "python"},
            safety_checks=True
        )
        
        assert function_call is not None
        assert function_call.function == "code_execution_tool"
        assert function_call.parameters["code"] == "print('test')"
        
        # Проверить валидацию
        is_valid, issues = FunctionCallProtocol.validate_function_call(function_call)
        assert is_valid or len(issues) == 0

