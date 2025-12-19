"""
Интеграционные тесты для WorkflowEngine
Проверяют управление состояниями workflow, переходы, валидацию
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.core.database import SessionLocal
from app.core.execution_context import ExecutionContext
from app.core.workflow_engine import WorkflowEngine, WorkflowState


@pytest.fixture
def db_session():
    """Фикстура для db session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def execution_context(db_session):
    """Фикстура для ExecutionContext"""
    workflow_id = str(uuid4())
    context = ExecutionContext(
        db=db_session,
        workflow_id=workflow_id,
        trace_id=None,
        session_id=None,
        user_id="test_user",
        metadata={}
    )
    return context


@pytest.fixture
def workflow_engine(execution_context):
    """Фикстура для WorkflowEngine"""
    return WorkflowEngine.from_context(execution_context)


class TestWorkflowEngineBasic:
    """Базовые тесты WorkflowEngine"""
    
    def test_initialization(self, workflow_engine, execution_context):
        """Тест инициализации workflow"""
        workflow_engine.initialize(
            user_request="Test request",
            username="test_user",
            interaction_type="test"
        )
        
        assert workflow_engine.get_current_state() == WorkflowState.INITIALIZED
        assert workflow_engine.workflow_id == execution_context.workflow_id
    
    def test_transition_to_parsing(self, workflow_engine):
        """Тест перехода в состояние PARSING"""
        workflow_engine.initialize("Test", "test_user")
        
        success = workflow_engine.transition_to(
            WorkflowState.PARSING,
            "Parsing request"
        )
        
        assert success is True
        assert workflow_engine.get_current_state() == WorkflowState.PARSING
    
    def test_transition_to_planning(self, workflow_engine):
        """Тест перехода в состояние PLANNING"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        
        success = workflow_engine.transition_to(
            WorkflowState.PLANNING,
            "Starting planning"
        )
        
        assert success is True
        assert workflow_engine.get_current_state() == WorkflowState.PLANNING
    
    def test_invalid_transition(self, workflow_engine):
        """Тест недопустимого перехода"""
        workflow_engine.initialize("Test", "test_user")
        
        # Попытка перейти из INITIALIZED напрямую в EXECUTING (недопустимо)
        success = workflow_engine.transition_to(
            WorkflowState.EXECUTING,
            "Invalid transition"
        )
        
        assert success is False
        assert workflow_engine.get_current_state() == WorkflowState.INITIALIZED
    
    def test_forced_transition(self, workflow_engine):
        """Тест принудительного перехода"""
        workflow_engine.initialize("Test", "test_user")
        
        # Принудительный переход (например, для ошибок)
        success = workflow_engine.transition_to(
            WorkflowState.FAILED,
            "Forced failure",
            force=True
        )
        
        assert success is True
        assert workflow_engine.get_current_state() == WorkflowState.FAILED
    
    def test_transition_history(self, workflow_engine):
        """Тест истории переходов"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Step 1")
        workflow_engine.transition_to(WorkflowState.PLANNING, "Step 2")
        
        history = workflow_engine.get_transition_history()
        
        assert len(history) == 2
        assert history[0].from_state == WorkflowState.INITIALIZED
        assert history[0].to_state == WorkflowState.PARSING
        assert history[1].from_state == WorkflowState.PARSING
        assert history[1].to_state == WorkflowState.PLANNING


class TestWorkflowEngineStateManagement:
    """Тесты управления состояниями"""
    
    def test_pause_and_resume(self, workflow_engine):
        """Тест паузы и возобновления"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        workflow_engine.transition_to(WorkflowState.PLANNING, "Planning")
        workflow_engine.transition_to(WorkflowState.APPROVED, "Approved")
        workflow_engine.transition_to(WorkflowState.EXECUTING, "Executing")
        
        # Пауза
        pause_success = workflow_engine.pause("User requested pause")
        assert pause_success is True
        assert workflow_engine.get_current_state() == WorkflowState.PAUSED
        
        # Возобновление
        resume_success = workflow_engine.resume()
        assert resume_success is True
        assert workflow_engine.get_current_state() == WorkflowState.EXECUTING
    
    def test_pause_from_wrong_state(self, workflow_engine):
        """Тест паузы из неправильного состояния"""
        workflow_engine.initialize("Test", "test_user")
        
        # Нельзя поставить на паузу из INITIALIZED
        pause_success = workflow_engine.pause("Test")
        assert pause_success is False
        assert workflow_engine.get_current_state() == WorkflowState.INITIALIZED
    
    def test_cancel(self, workflow_engine):
        """Тест отмены workflow"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        
        cancel_success = workflow_engine.cancel("User cancelled")
        assert cancel_success is True
        assert workflow_engine.get_current_state() == WorkflowState.CANCELLED
    
    def test_cancel_from_completed(self, workflow_engine):
        """Тест отмены из завершенного состояния"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        workflow_engine.transition_to(WorkflowState.PLANNING, "Planning")
        workflow_engine.transition_to(WorkflowState.APPROVED, "Approved")
        workflow_engine.transition_to(WorkflowState.EXECUTING, "Executing")
        workflow_engine.mark_completed("Done")
        
        # Нельзя отменить завершенный workflow
        cancel_success = workflow_engine.cancel("Test")
        assert cancel_success is False
        assert workflow_engine.get_current_state() == WorkflowState.COMPLETED
    
    def test_mark_completed(self, workflow_engine):
        """Тест отметки как завершенный"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        workflow_engine.transition_to(WorkflowState.PLANNING, "Planning")
        workflow_engine.transition_to(WorkflowState.APPROVED, "Approved")
        workflow_engine.transition_to(WorkflowState.EXECUTING, "Executing")
        
        success = workflow_engine.mark_completed("Task completed successfully")
        assert success is True
        assert workflow_engine.get_current_state() == WorkflowState.COMPLETED
    
    def test_mark_failed(self, workflow_engine):
        """Тест отметки как проваленный"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        
        success = workflow_engine.mark_failed(
            error="Test error",
            error_details={"code": "TEST_ERROR"}
        )
        assert success is True
        assert workflow_engine.get_current_state() == WorkflowState.FAILED
    
    def test_retry_after_failure(self, workflow_engine):
        """Тест повтора после ошибки"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        workflow_engine.mark_failed("Error occurred")
        
        retry_success = workflow_engine.retry("Retrying after fix")
        assert retry_success is True
        assert workflow_engine.get_current_state() == WorkflowState.RETRYING
    
    def test_retry_from_wrong_state(self, workflow_engine):
        """Тест повтора из неправильного состояния"""
        workflow_engine.initialize("Test", "test_user")
        
        # Нельзя повторить из INITIALIZED
        retry_success = workflow_engine.retry("Test")
        assert retry_success is False
        assert workflow_engine.get_current_state() == WorkflowState.INITIALIZED


class TestWorkflowEngineApprovalFlow:
    """Тесты workflow с одобрением"""
    
    def test_approval_pending_flow(self, workflow_engine):
        """Тест workflow с ожиданием одобрения"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        workflow_engine.transition_to(WorkflowState.PLANNING, "Planning")
        
        # Переход в ожидание одобрения
        success = workflow_engine.transition_to(
            WorkflowState.APPROVAL_PENDING,
            "Plan created, awaiting approval"
        )
        assert success is True
        assert workflow_engine.get_current_state() == WorkflowState.APPROVAL_PENDING
        
        # Одобрение
        success = workflow_engine.transition_to(
            WorkflowState.APPROVED,
            "Plan approved"
        )
        assert success is True
        assert workflow_engine.get_current_state() == WorkflowState.APPROVED
    
    def test_approval_to_execution(self, workflow_engine):
        """Тест перехода от одобрения к выполнению"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        workflow_engine.transition_to(WorkflowState.PLANNING, "Planning")
        workflow_engine.transition_to(WorkflowState.APPROVAL_PENDING, "Awaiting approval")
        workflow_engine.transition_to(WorkflowState.APPROVED, "Approved")
        
        success = workflow_engine.transition_to(
            WorkflowState.EXECUTING,
            "Starting execution"
        )
        assert success is True
        assert workflow_engine.get_current_state() == WorkflowState.EXECUTING


class TestWorkflowEngineStateInfo:
    """Тесты получения информации о состоянии"""
    
    def test_get_state_info(self, workflow_engine):
        """Тест получения информации о состоянии"""
        workflow_engine.initialize("Test", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        
        state_info = workflow_engine.get_state_info()
        
        assert state_info["workflow_id"] == workflow_engine.workflow_id
        assert state_info["current_state"] == WorkflowState.PARSING.value
        assert state_info["transitions_count"] == 1
        assert "allowed_next_states" in state_info
    
    def test_can_transition_to(self, workflow_engine):
        """Тест проверки возможности перехода"""
        workflow_engine.initialize("Test", "test_user")
        
        # Из INITIALIZED можно перейти в PARSING
        assert workflow_engine.can_transition_to(WorkflowState.PARSING) is True
        
        # Из INITIALIZED нельзя перейти в EXECUTING
        assert workflow_engine.can_transition_to(WorkflowState.EXECUTING) is False
        
        # Переход в PARSING
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        
        # Из PARSING можно перейти в PLANNING
        assert workflow_engine.can_transition_to(WorkflowState.PLANNING) is True


class TestWorkflowEngineFullFlow:
    """Тесты полного workflow"""
    
    def test_complete_workflow_success(self, workflow_engine):
        """Тест успешного завершения полного workflow"""
        workflow_engine.initialize("Create a function", "test_user")
        
        # Парсинг
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing request")
        assert workflow_engine.get_current_state() == WorkflowState.PARSING
        
        # Планирование
        workflow_engine.transition_to(WorkflowState.PLANNING, "Generating plan")
        assert workflow_engine.get_current_state() == WorkflowState.PLANNING
        
        # Автоматическое одобрение (низкий риск)
        workflow_engine.transition_to(WorkflowState.APPROVED, "Auto-approved")
        assert workflow_engine.get_current_state() == WorkflowState.APPROVED
        
        # Выполнение
        workflow_engine.transition_to(WorkflowState.EXECUTING, "Executing plan")
        assert workflow_engine.get_current_state() == WorkflowState.EXECUTING
        
        # Завершение
        workflow_engine.mark_completed("Function created successfully")
        assert workflow_engine.get_current_state() == WorkflowState.COMPLETED
        
        # Проверка истории
        history = workflow_engine.get_transition_history()
        assert len(history) == 5
    
    def test_workflow_with_approval(self, workflow_engine):
        """Тест workflow с ожиданием одобрения"""
        workflow_engine.initialize("Complex task", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        workflow_engine.transition_to(WorkflowState.PLANNING, "Planning")
        
        # Требуется одобрение
        workflow_engine.transition_to(WorkflowState.APPROVAL_PENDING, "Awaiting approval")
        assert workflow_engine.get_current_state() == WorkflowState.APPROVAL_PENDING
        
        # Одобрение
        workflow_engine.transition_to(WorkflowState.APPROVED, "Approved")
        assert workflow_engine.get_current_state() == WorkflowState.APPROVED
        
        # Выполнение
        workflow_engine.transition_to(WorkflowState.EXECUTING, "Executing")
        assert workflow_engine.get_current_state() == WorkflowState.EXECUTING
    
    def test_workflow_with_failure_and_retry(self, workflow_engine):
        """Тест workflow с ошибкой и повтором"""
        workflow_engine.initialize("Test task", "test_user")
        workflow_engine.transition_to(WorkflowState.PARSING, "Parsing")
        workflow_engine.transition_to(WorkflowState.PLANNING, "Planning")
        workflow_engine.transition_to(WorkflowState.APPROVED, "Approved")
        workflow_engine.transition_to(WorkflowState.EXECUTING, "Executing")
        
        # Ошибка
        workflow_engine.mark_failed("Execution error")
        assert workflow_engine.get_current_state() == WorkflowState.FAILED
        
        # Повтор
        workflow_engine.retry("Retrying after fix")
        assert workflow_engine.get_current_state() == WorkflowState.RETRYING
        
        # Возобновление выполнения
        workflow_engine.transition_to(WorkflowState.EXECUTING, "Retrying execution")
        assert workflow_engine.get_current_state() == WorkflowState.EXECUTING
        
        # Успешное завершение
        workflow_engine.mark_completed("Completed after retry")
        assert workflow_engine.get_current_state() == WorkflowState.COMPLETED
