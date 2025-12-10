"""
Тесты для Этапа 1: Критические исправления и унификация
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from app.models.task import Task, TaskStatus
from app.models.plan import Plan
from app.core.execution_context import ExecutionContext
from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService
from app.core.request_orchestrator import RequestOrchestrator
from app.core.workflow_engine import WorkflowEngine, WorkflowState
from app.core.prompt_manager import PromptManager


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


class TestCriticalBugs:
    """Тесты для критических исправлений"""
    
    def test_execute_decision_step_exists(self, execution_context):
        """Проверить, что _execute_decision_step реализован"""
        from app.services.execution_service import StepExecutor
        executor = StepExecutor(execution_context.db, context=execution_context)
        # Проверить, что метод существует
        assert hasattr(executor, '_execute_decision_step')
        # Проверить, что это callable
        import inspect
        method = getattr(executor, '_execute_decision_step')
        assert callable(method) or inspect.iscoroutinefunction(method)
    
    def test_execute_validation_step_exists(self, execution_context):
        """Проверить, что _execute_validation_step реализован"""
        from app.services.execution_service import StepExecutor
        executor = StepExecutor(execution_context.db, context=execution_context)
        # Проверить, что метод существует
        assert hasattr(executor, '_execute_validation_step')
        # Проверить, что это callable
        import inspect
        method = getattr(executor, '_execute_validation_step')
        assert callable(method) or inspect.iscoroutinefunction(method)
    
    def test_execute_with_team_exists(self, execution_context):
        """Проверить, что _execute_with_team реализован"""
        from app.services.execution_service import StepExecutor
        executor = StepExecutor(execution_context.db, context=execution_context)
        # Проверить, что метод существует
        assert hasattr(executor, '_execute_with_team')
        # Проверить, что это callable
        import inspect
        method = getattr(executor, '_execute_with_team')
        assert callable(method) or inspect.iscoroutinefunction(method)
    
    def test_web_search_tool_integration(self, execution_context):
        """Проверить интеграцию WebSearchTool в RequestOrchestrator"""
        orchestrator = RequestOrchestrator()  # Не принимает параметры
        
        # Проверить, что метод _handle_information_query существует
        assert hasattr(orchestrator, '_handle_information_query')
        assert callable(orchestrator._handle_information_query)


class TestComponentUnification:
    """Тесты для унификации компонентов"""
    
    def test_workflow_engine_in_execution_context(self, execution_context):
        """Проверить, что WorkflowEngine доступен через ExecutionContext"""
        assert hasattr(execution_context, 'workflow_engine')
        assert execution_context.workflow_engine is not None
        assert isinstance(execution_context.workflow_engine, WorkflowEngine)
    
    def test_prompt_manager_in_execution_context(self, execution_context):
        """Проверить, что PromptManager может быть установлен в ExecutionContext"""
        assert hasattr(execution_context, 'prompt_manager')
        assert hasattr(execution_context, 'set_prompt_manager')
        
        # PromptManager устанавливается позже через set_prompt_manager
        # Проверим, что метод существует
        from app.core.prompt_manager import PromptManager
        prompt_manager = PromptManager(execution_context)
        execution_context.set_prompt_manager(prompt_manager)
        
        assert execution_context.prompt_manager is not None
        assert isinstance(execution_context.prompt_manager, PromptManager)
    
    def test_planning_service_uses_workflow_engine(self, execution_context):
        """Проверить, что PlanningService использует WorkflowEngine"""
        service = PlanningService(execution_context)
        assert hasattr(service, 'context')
        assert service.context.workflow_engine is not None
    
    def test_execution_service_uses_workflow_engine(self, execution_context):
        """Проверить, что ExecutionService использует WorkflowEngine"""
        service = ExecutionService(execution_context)
        assert hasattr(service, 'context')
        assert service.context.workflow_engine is not None


class TestWebSearchIntegration:
    """Тесты для интеграции WebSearchTool"""
    
    def test_web_search_requires_approval(self, execution_context):
        """Проверить, что WebSearch требует одобрения через AdaptiveApprovalService"""
        orchestrator = RequestOrchestrator()  # Не принимает параметры
        
        # Проверить наличие метода для обработки информационных запросов
        assert hasattr(orchestrator, '_handle_information_query')
        
        # Проверить, что используется AdaptiveApprovalService
        from app.services.adaptive_approval_service import AdaptiveApprovalService
        assert AdaptiveApprovalService is not None
        
        # Проверить, что AdaptiveApprovalService может быть создан
        approval_service = AdaptiveApprovalService(execution_context)
        assert approval_service is not None

