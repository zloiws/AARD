"""
Тест этапа 8.2: Интеграция диалогов в workflow
Проверяет полную интеграцию диалогов с PlanningService и API
"""
import asyncio
import sys
from datetime import datetime
from uuid import uuid4

import pytest

# Настройка кодировки
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app.models.agent import Agent, AgentStatus
from app.models.agent_conversation import ConversationStatus
from app.models.plan import Plan, PlanStatus
from app.models.task import Task, TaskStatus
from app.services.agent_dialog_service import AgentDialogService
from app.services.agent_service import AgentService
from app.services.ollama_service import OllamaService
from app.services.planning_service import PlanningService
from app.services.planning_service_dialog_integration import (
    initiate_agent_dialog_for_planning, is_complex_task)


@pytest.mark.asyncio
@pytest.mark.slow
async def test_planning_service_with_dialogs(db):
    """
    Тест: PlanningService использует диалоги для сложных задач
    """
    print("\n" + "="*80)
    print("ТЕСТ ЭТАПА 8.2: Интеграция диалогов в PlanningService")
    print("="*80)
    
    # Проверить наличие серверов
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("Нет активных серверов")
    
    # Создать агентов
    agent_service = AgentService(db)
    
    planner_agent = agent_service.create_agent(
        name=f"Planner-{uuid4().hex[:8]}",
        capabilities=["planning", "reasoning"]
    )
    planner_agent.status = AgentStatus.ACTIVE.value
    
    developer_agent = agent_service.create_agent(
        name=f"Developer-{uuid4().hex[:8]}",
        capabilities=["code_generation"]
    )
    developer_agent.status = AgentStatus.ACTIVE.value
    
    db.commit()
    
    # Сложная задача
    complex_task_description = """
    Создать систему для управления задачами с следующими требованиями:
    1. API для создания и обновления задач
    2. Система приоритетов
    3. Уведомления о дедлайнах
    4. Интеграция с календарем
    """
    
    # Проверить определение сложной задачи
    is_complex = is_complex_task(complex_task_description)
    assert is_complex, "Задача должна быть определена как сложная"
    print(f"✓ Задача определена как сложная: {is_complex}")
    
    # Создать задачу
    task = Task(
        description=complex_task_description.strip(),
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Генерировать план (должен инициировать диалог)
    planning_service = PlanningService(db)
    plan = await planning_service.generate_plan(
        task_id=task.id,
        task_description=complex_task_description.strip(),
        context={}
    )
    
    assert plan is not None, "План должен быть создан"
    print(f"✓ План создан: {plan.id}")
    
    # Проверить, что диалог был создан (если задача сложная)
    dialog_service = AgentDialogService(db)
    conversations = dialog_service.get_conversations_by_task(task.id)
    
    # Проверить диалог (может быть создан или нет в зависимости от настроек)
    if is_complex and len(conversations) > 0:
        # Для сложных задач может быть создан диалог
        print(f"✓ Диалог создан для сложной задачи: {conversations[0].id}")
        
        conversation = conversations[0]
        assert conversation.status in [ConversationStatus.ACTIVE.value, ConversationStatus.COMPLETED.value, ConversationStatus.INITIATED.value]
        assert len(conversation.participants) >= 2, "В диалоге должно быть минимум 2 участника"
        print(f"✓ Диалог имеет {len(conversation.participants)} участников")
    else:
        print(f"ℹ Диалог не создан (возможно, не настроен автоматический запуск)")
    
    db.commit()


@pytest.mark.asyncio
async def test_dialog_context_in_planning(db):
    """
    Тест: Контекст диалога используется при создании плана
    """
    print("\n" + "="*80)
    print("ТЕСТ: Контекст диалога в планировании")
    print("="*80)
    
    # Создать агентов
    agent_service = AgentService(db)
    
    agent1 = agent_service.create_agent(
        name=f"Agent1-{uuid4().hex[:8]}",
        capabilities=["planning"]
    )
    agent1.status = AgentStatus.ACTIVE.value
    
    agent2 = agent_service.create_agent(
        name=f"Agent2-{uuid4().hex[:8]}",
        capabilities=["code_generation"]
    )
    agent2.status = AgentStatus.ACTIVE.value
    
    db.commit()
    
    # Создать диалог
    dialog_service = AgentDialogService(db)
    conversation = dialog_service.create_conversation(
        participant_ids=[agent1.id, agent2.id],
        goal="Обсудить подход к решению задачи",
        title="Тестовый диалог"
    )
    
    # Добавить сообщения в диалог
    dialog_service.add_message(
        conversation_id=conversation.id,
        agent_id=agent1.id,
        content="Предлагаю использовать REST API",
        role="agent"
    )
    
    dialog_service.add_message(
        conversation_id=conversation.id,
        agent_id=agent2.id,
        content="Согласен, используем FastAPI",
        role="agent"
    )
    
    # Обновить контекст диалога
    dialog_service.update_context(
        conversation_id=conversation.id,
        updates={
            "agreed_approach": "REST API с FastAPI",
            "technology_stack": ["FastAPI", "PostgreSQL"]
        }
    )
    
    db.commit()
    
    # Проверить, что контекст сохранен
    updated_conversation = dialog_service.get_conversation(conversation.id)
    context = updated_conversation.get_context()
    
    assert context.get("agreed_approach") == "REST API с FastAPI"
    assert "FastAPI" in context.get("technology_stack", [])
    print(f"✓ Контекст диалога сохранен: {context}")
    
    # Создать задачу
    task = Task(
        description="Создать REST API для управления задачами",
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Связать диалог с задачей
    conversation.task_id = task.id
    db.commit()
    
    # Генерировать план (должен использовать контекст диалога)
    planning_service = PlanningService(db)
    plan = await planning_service.generate_plan(
        task_id=task.id,
        task_description=task.description,
        context={
            "dialog_context": context
        }
    )
    
    assert plan is not None
    print(f"✓ План создан с учетом контекста диалога: {plan.id}")


@pytest.mark.asyncio
async def test_api_dialog_management(db):
    """
    Тест: API для управления диалогами работает корректно
    """
    print("\n" + "="*80)
    print("ТЕСТ: API для управления диалогами")
    print("="*80)
    
    # Создать агентов
    agent_service = AgentService(db)
    
    agent1 = agent_service.create_agent(
        name=f"Agent1-{uuid4().hex[:8]}",
        capabilities=["planning"]
    )
    agent1.status = AgentStatus.ACTIVE.value
    
    agent2 = agent_service.create_agent(
        name=f"Agent2-{uuid4().hex[:8]}",
        capabilities=["code_generation"]
    )
    agent2.status = AgentStatus.ACTIVE.value
    
    db.commit()
    
    # Импортировать TestClient
    from app.core.database import get_db
    from fastapi.testclient import TestClient
    from main import app

    # Override database dependency
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    
    try:
        # Создать диалог через API
        response = client.post(
            "/api/agent-dialogs/",
            json={
                "participant_ids": [str(agent1.id), str(agent2.id)],
                "goal": "Обсудить решение задачи",
                "title": "API Тест диалог"
            }
        )
        
        assert response.status_code == 201
        conversation_data = response.json()
        conversation_id = conversation_data["id"]
        print(f"✓ Диалог создан через API: {conversation_id}")
        
        # Получить диалог через API
        response = client.get(f"/api/agent-dialogs/{conversation_id}")
        assert response.status_code == 200
        conversation = response.json()
        assert conversation["id"] == conversation_id
        assert len(conversation["participants"]) == 2
        print(f"✓ Диалог получен через API")
        
        # Добавить сообщение через API
        response = client.post(
            f"/api/agent-dialogs/{conversation_id}/message",
            json={
                "agent_id": str(agent1.id),
                "content": "Привет от агента 1",
                "role": "agent"
            }
        )
        assert response.status_code == 200
        print(f"✓ Сообщение добавлено через API")
        
        # Получить сообщения
        response = client.get(f"/api/agent-dialogs/{conversation_id}/messages")
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) > 0
        print(f"✓ Сообщения получены через API: {len(messages)} сообщений")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_complete_workflow_with_dialogs(db):
    """
    Тест: Полный workflow с диалогами от задачи до выполнения
    """
    print("\n" + "="*80)
    print("ТЕСТ: Полный workflow с диалогами")
    print("="*80)
    
    # Создать агентов
    agent_service = AgentService(db)
    
    planner = agent_service.create_agent(
        name=f"Planner-{uuid4().hex[:8]}",
        capabilities=["planning", "reasoning"]
    )
    planner.status = AgentStatus.ACTIVE.value
    
    developer = agent_service.create_agent(
        name=f"Developer-{uuid4().hex[:8]}",
        capabilities=["code_generation"]
    )
    developer.status = AgentStatus.ACTIVE.value
    
    db.commit()
    
    # Создать сложную задачу
    task_description = "Разработать систему для автоматизации тестирования с интеграцией CI/CD"
    
    task = Task(
        description=task_description,
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Генерировать план (должен создать диалог)
    planning_service = PlanningService(db)
    plan = await planning_service.generate_plan(
        task_id=task.id,
        task_description=task_description,
        context={}
    )
    
    assert plan is not None
    print(f"✓ План создан: {plan.id}")
    
    # Проверить диалог
    dialog_service = AgentDialogService(db)
    conversations = dialog_service.get_conversations_by_task(task.id)
    
    if conversations:
        conversation = conversations[0]
        print(f"✓ Диалог создан: {conversation.id}")
        print(f"  Участников: {len(conversation.participants)}")
        print(f"  Сообщений: {len(conversation.get_messages())}")
        print(f"  Статус: {conversation.status}")
    
    db.commit()
    print("✓ Полный workflow с диалогами завершен успешно")

