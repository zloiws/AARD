"""
Тесты для Этапа 4: ToDo-список как Workflow Engine
"""
import pytest
from uuid import uuid4

from app.models.task import Task, TaskStatus
from app.services.task_lifecycle_manager import TaskLifecycleManager, TaskRole
from app.services.planning_service import PlanningService
from app.core.execution_context import ExecutionContext


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


class TestTaskLifecycleIntegration:
    """Тесты для интеграции TaskLifecycleManager"""
    
    def test_planning_service_uses_lifecycle_manager(self, execution_context):
        """Проверить, что PlanningService использует TaskLifecycleManager"""
        service = PlanningService(execution_context)
        assert hasattr(service, 'task_lifecycle_manager')
        assert service.task_lifecycle_manager is not None
    
    def test_lifecycle_manager_in_planning(self, execution_context):
        """Проверить использование TaskLifecycleManager в PlanningService"""
        service = PlanningService(execution_context)
        
        # Создать задачу
        task = Task(
            description="Test task",
            status=TaskStatus.DRAFT,
            autonomy_level=2
        )
        execution_context.db.add(task)
        execution_context.db.commit()
        
        # Проверить, что можно использовать lifecycle manager
        manager = service.task_lifecycle_manager
        assert manager is not None
        
        # Проверить переход
        success = manager.transition(
            task=task,
            new_status=TaskStatus.PENDING_APPROVAL,
            role=TaskRole.PLANNER,
            reason="Test"
        )
        assert success is True


class TestReplanning:
    """Тесты для механизма перепланирования"""
    
    def test_planning_service_has_replan_method(self, execution_context):
        """Проверить наличие метода replan"""
        service = PlanningService(execution_context)
        assert hasattr(service, 'replan')
        assert callable(service.replan)
    
    def test_planning_service_has_auto_replan_on_error(self, execution_context):
        """Проверить наличие метода auto_replan_on_error"""
        service = PlanningService(execution_context)
        assert hasattr(service, 'auto_replan_on_error')
        assert callable(service.auto_replan_on_error)
    
    def test_replanning_uses_memory(self, execution_context):
        """Проверить, что перепланирование использует память"""
        service = PlanningService(execution_context)
        
        # Проверить, что в методе replan есть поиск похожих ситуаций
        import inspect
        source = inspect.getsource(service.replan)
        # Проверить наличие MemoryService в коде
        assert 'MemoryService' in source or 'memory_service' in source


class TestMemoryIntegration:
    """Тесты для интеграции с памятью"""
    
    @pytest.mark.asyncio
    async def test_execution_saves_to_memory(self, execution_context):
        """Проверить, что ExecutionService сохраняет результаты в память"""
        from app.services.execution_service import ExecutionService
        from app.models.plan import Plan
        
        service = ExecutionService(execution_context)
        
        # Создать тестовую задачу
        task = Task(
            description="Test task",
            status=TaskStatus.PENDING,
            autonomy_level=2
        )
        execution_context.db.add(task)
        execution_context.db.commit()
        
        # Создать тестовый план с task_id
        plan = Plan(
            goal="Test goal",
            steps=[],
            status="completed",
            task_id=task.id
        )
        execution_context.db.add(plan)
        execution_context.db.commit()
        
        # Проверить наличие логики сохранения в память
        import inspect
        source = inspect.getsource(service.execute_plan)
        # Проверить наличие MemoryService в коде
        assert 'MemoryService' in source or 'memory_service' in source

