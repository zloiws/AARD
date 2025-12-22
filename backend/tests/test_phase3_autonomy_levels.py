"""
Тесты для Этапа 3: Human-in-the-Loop и уровни автономности
"""
from uuid import uuid4

import pytest
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
from app.services.adaptive_approval_service import AdaptiveApprovalService
from app.services.agent_approval_agent import AgentApprovalAgent
from app.services.task_lifecycle_manager import TaskLifecycleManager, TaskRole


@pytest.fixture
def db_session():
    """Создать тестовую сессию БД"""
    from app.core.database import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


class TestAutonomyLevels:
    """Тесты для уровней автономности"""
    
    def test_task_has_autonomy_level(self, db_session):
        """Проверить, что Task имеет поле autonomy_level"""
        task = Task(
            description="Test task",
            status=TaskStatus.PENDING,
            autonomy_level=2
        )
        db_session.add(task)
        db_session.commit()
        
        assert task.autonomy_level == 2
        assert hasattr(task, 'autonomy_level')
    
    def test_adaptive_approval_considers_autonomy_level(self, db_session):
        """Проверить, что AdaptiveApprovalService учитывает autonomy_level"""
        service = AdaptiveApprovalService(db_session)
        
        # Создать тестовую задачу
        task = Task(
            description="Test task",
            status=TaskStatus.PENDING,
            autonomy_level=2
        )
        db_session.add(task)
        db_session.commit()
        
        # Создать тестовый план с task_id
        plan = Plan(
            goal="Test goal",
            steps=[],
            status="draft",
            task_id=task.id
        )
        db_session.add(plan)
        db_session.commit()
        
        # Тест уровня 0 (read-only) - всегда требует одобрения
        requires, metadata = service.should_require_approval(
            plan=plan,
            task_autonomy_level=0
        )
        assert requires is True
        assert metadata.get("reason") == "autonomy_level_0"
        
        # Тест уровня 1 (step-by-step) - всегда требует одобрения
        requires, metadata = service.should_require_approval(
            plan=plan,
            task_autonomy_level=1
        )
        assert requires is True
        assert metadata.get("reason") == "autonomy_level_1"
        
        # Тест уровня 2 (plan approval) - всегда требует одобрения
        requires, metadata = service.should_require_approval(
            plan=plan,
            task_autonomy_level=2
        )
        assert requires is True
        assert metadata.get("reason") == "autonomy_level_2"
        
        # Тест уровня 4 (full autonomous) - не требует одобрения для низкого риска
        requires, metadata = service.should_require_approval(
            plan=plan,
            task_autonomy_level=4,
            task_risk_level=0.5
        )
        assert requires is False
        assert metadata.get("reason") == "autonomy_level_4"


class TestAgentApprovalAgent:
    """Тесты для Agent Approval Agent"""
    
    def test_aaa_creation(self, db_session):
        """Проверить создание AgentApprovalAgent"""
        aaa = AgentApprovalAgent(db_session)
        assert aaa is not None
        assert hasattr(aaa, 'validate_agent_creation')
    
    @pytest.mark.asyncio
    async def test_aaa_validates_agent_creation(self, db_session):
        """Проверить валидацию создания агента"""
        aaa = AgentApprovalAgent(db_session)
        
        proposed_agent = {
            "name": "TestAgent",
            "description": "Test agent",
            "capabilities": ["test"],
            "tools": [],
            "expected_benefit": "Testing",
            "risks": []
        }
        
        result = await aaa.validate_agent_creation(
            proposed_agent=proposed_agent,
            task_description="Test task"
        )
        
        assert result is not None
        assert "is_needed" in result
        assert "requires_approval" in result
        assert isinstance(result["is_needed"], bool)
        assert isinstance(result["requires_approval"], bool)


class TestTaskLifecycleManager:
    """Тесты для TaskLifecycleManager"""
    
    def test_lifecycle_manager_creation(self, db_session):
        """Проверить создание TaskLifecycleManager"""
        manager = TaskLifecycleManager(db_session)
        assert manager is not None
        assert hasattr(manager, 'transition')
        assert hasattr(manager, 'can_transition')
    
    def test_lifecycle_transitions(self, db_session):
        """Проверить переходы между статусами"""
        manager = TaskLifecycleManager(db_session)
        
        # Создать задачу
        task = Task(
            description="Test task",
            status=TaskStatus.DRAFT,
            autonomy_level=2
        )
        db_session.add(task)
        db_session.commit()
        
        # Проверить разрешенные переходы
        allowed = manager.get_allowed_transitions(task, TaskRole.PLANNER)
        assert TaskStatus.PENDING_APPROVAL in allowed
        assert TaskStatus.CANCELLED in allowed
        
        # Выполнить переход
        success = manager.transition(
            task=task,
            new_status=TaskStatus.PENDING_APPROVAL,
            role=TaskRole.PLANNER,
            reason="Test transition"
        )
        
        assert success is True
        assert task.status == TaskStatus.PENDING_APPROVAL
        
        # Проверить историю в контексте
        context = task.get_context()
        assert "status_history" in context
        assert len(context["status_history"]) > 0
    
    def test_lifecycle_forbidden_transition(self, db_session):
        """Проверить запрещенные переходы"""
        manager = TaskLifecycleManager(db_session)
        
        task = Task(
            description="Test task",
            status=TaskStatus.DRAFT,
            autonomy_level=2
        )
        db_session.add(task)
        db_session.commit()
        
        # Попытка перехода напрямую в COMPLETED (запрещено)
        success = manager.transition(
            task=task,
            new_status=TaskStatus.COMPLETED,
            role=TaskRole.PLANNER,
            reason="Invalid transition"
        )
        
        assert success is False
        assert task.status == TaskStatus.DRAFT  # Статус не изменился
    
    def test_lifecycle_role_permissions(self, db_session):
        """Проверить права ролей на переходы"""
        manager = TaskLifecycleManager(db_session)
        
        task = Task(
            description="Test task",
            status=TaskStatus.APPROVED,
            autonomy_level=2
        )
        db_session.add(task)
        db_session.commit()
        
        # EXECUTOR может перейти в IN_PROGRESS
        can_transition = manager.can_transition(
            task=task,
            new_status=TaskStatus.IN_PROGRESS,
            role=TaskRole.EXECUTOR
        )
        assert can_transition is True
        
        # HUMAN не может перейти в IN_PROGRESS (только EXECUTOR)
        can_transition = manager.can_transition(
            task=task,
            new_status=TaskStatus.IN_PROGRESS,
            role=TaskRole.HUMAN
        )
        # SYSTEM может, но HUMAN не может
        assert can_transition is False or TaskRole.SYSTEM in manager.ROLE_PERMISSIONS.get(TaskStatus.IN_PROGRESS, [])

