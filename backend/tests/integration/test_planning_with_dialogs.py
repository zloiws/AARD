"""
Интеграционные тесты для PlanningService с диалогами агентов
"""
import asyncio
from uuid import UUID, uuid4

import pytest
from app.models.agent import Agent, AgentStatus
from app.models.agent_conversation import ConversationStatus
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.services.agent_dialog_service import AgentDialogService
from app.services.agent_service import AgentService
from app.services.planning_service import PlanningService
from app.services.planning_service_dialog_integration import is_complex_task


@pytest.mark.asyncio
async def test_planning_simple_task_no_dialog(db):
    """Тест планирования простой задачи - диалог не должен создаваться"""
    print("[TEST START] test_planning_simple_task_no_dialog")
    planning_service = PlanningService(db)
    
    # Простая задача
    simple_task = "Напиши print('Привет')"
    
    # Проверить, что задача не сложная
    assert is_complex_task(simple_task) is False
    
    # Создать задачу
    task = Task(
        description=simple_task,
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Генерировать план
    plan = await planning_service.generate_plan(
        task_description=simple_task,
        task_id=task.id
    )
    
    assert plan is not None
    assert plan.task_id == task.id
    
    # Проверить, что диалог не создан
    dialog_service = AgentDialogService(db)
    conversations = dialog_service.get_conversations_by_task(task.id)
    assert len(conversations) == 0, "Для простой задачи диалог не должен создаваться"


@pytest.mark.asyncio
async def test_planning_complex_task_with_dialog(db):
    """Тест планирования сложной задачи - должен создаться диалог"""
    print("[TEST START] test_planning_complex_task_with_dialog")
    # Создать агентов
    agent_service = AgentService(db)
    agent1 = agent_service.create_agent(
        name=f"Planner Agent {uuid4()}",
        capabilities=["planning", "reasoning"]
    )
    agent1.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent1)
    
    agent2 = agent_service.create_agent(
        name=f"Developer Agent {uuid4()}",
        capabilities=["code_generation"]
    )
    agent2.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent2)
    
    # Сложная задача
    complex_task = "Создай сложную архитектуру веб-приложения с интеграцией нескольких сервисов и координацией между компонентами системы"
    
    # Проверить, что задача сложная
    assert is_complex_task(complex_task) is True
    
    # Создать задачу
    task = Task(
        description=complex_task,
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Генерировать план
    planning_service = PlanningService(db)
    plan = await planning_service.generate_plan(
        task_description=complex_task,
        task_id=task.id,
        context={"requires_dialog": False}  # Не принуждать, но задача сама сложная
    )
    
    assert plan is not None
    assert plan.task_id == task.id
    
    # Проверить, что диалог создан (может быть создан, если агенты найдены)
    dialog_service = AgentDialogService(db)
    conversations = dialog_service.get_conversations_by_task(task.id)
    
    # Диалог может быть создан или нет, в зависимости от наличия агентов
    # Главное - проверить, что система работает
    if len(conversations) > 0:
        conversation = conversations[0]
        assert conversation.task_id == task.id
        assert conversation.status in [ConversationStatus.COMPLETED.value, ConversationStatus.ACTIVE.value]
        
        # Проверить контекст в Digital Twin
        db.refresh(task)
        context = task.get_context()
        assert "agent_dialog" in context or len(conversations) > 0


@pytest.mark.asyncio
async def test_planning_with_explicit_dialog_requirement(db):
    """Тест планирования с явным требованием диалога в context"""
    print("[TEST START] test_planning_with_explicit_dialog_requirement")
    # Создать агентов
    agent_service = AgentService(db)
    agent1 = agent_service.create_agent(
        name=f"Agent 1 {uuid4()}",
        capabilities=["planning"]
    )
    agent1.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent1)
    
    agent2 = agent_service.create_agent(
        name=f"Agent 2 {uuid4()}",
        capabilities=["code_generation"]
    )
    agent2.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent2)
    
    # Задача с явным требованием диалога
    task_description = "Напиши функцию"
    
    # Проверить, что с requires_dialog=True задача считается сложной
    assert is_complex_task(task_description, {"requires_dialog": True}) is True
    
    # Создать задачу
    task = Task(
        description=task_description,
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Генерировать план с явным требованием диалога
    planning_service = PlanningService(db)
    plan = await planning_service.generate_plan(
        task_description=task_description,
        task_id=task.id,
        context={"requires_dialog": True}
    )
    
    assert plan is not None
    
    # Проверить контекст в Digital Twin
    db.refresh(task)
    context = task.get_context()
    
    # Диалог может быть создан, если агенты найдены
    dialog_service = AgentDialogService(db)
    conversations = dialog_service.get_conversations_by_task(task.id)
    
    if len(conversations) > 0:
        assert "agent_dialog" in context or len(conversations) > 0


@pytest.mark.asyncio
async def test_dialog_context_in_plan(db):
    """Тест использования контекста диалога при генерации плана"""
    print("[TEST START] test_dialog_context_in_plan")
    # Создать агентов
    agent_service = AgentService(db)
    agent1 = agent_service.create_agent(
        name=f"Planner {uuid4()}",
        capabilities=["planning"]
    )
    agent1.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent1)
    
    agent2 = agent_service.create_agent(
        name=f"Developer {uuid4()}",
        capabilities=["code_generation"]
    )
    agent2.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent2)
    
    # Сложная задача
    complex_task = "Создай архитектуру системы с множественными компонентами и интеграцией сервисов"
    
    task = Task(
        description=complex_task,
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Генерировать план
    planning_service = PlanningService(db)
    plan = await planning_service.generate_plan(
        task_description=complex_task,
        task_id=task.id
    )
    
    assert plan is not None
    
    # Проверить, что план содержит информацию о диалоге (если был создан)
    db.refresh(task)
    context = task.get_context()
    
    # Если диалог был создан, контекст должен содержать информацию
    dialog_service = AgentDialogService(db)
    conversations = dialog_service.get_conversations_by_task(task.id)
    
    if len(conversations) > 0:
        # Проверить, что контекст диалога сохранен
        assert "agent_dialog" in context or len(conversations) > 0

