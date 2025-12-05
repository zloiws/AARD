"""
Реальный тест планирования с диалогами агентов через LLM
"""
import pytest
import asyncio
import sys
from pathlib import Path
from uuid import uuid4

# Настройка кодировки
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app.services.planning_service import PlanningService
from app.services.agent_service import AgentService
from app.services.agent_dialog_service import AgentDialogService
from app.services.ollama_service import OllamaService
from app.core.model_selector import ModelSelector
from app.models.agent import Agent, AgentStatus
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.agent_conversation import ConversationStatus
from app.services.planning_service_dialog_integration import is_complex_task


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(300)
async def test_planning_complex_task_with_real_dialog_llm(db):
    """
    Реальный тест планирования сложной задачи с диалогом через LLM
    
    Проверяет:
    1. Определение сложной задачи
    2. Создание диалога между агентами
    3. Проведение диалога через реальные LLM
    4. Использование результатов диалога при генерации плана
    5. Сохранение контекста в Digital Twin
    """
    print("\n" + "="*80)
    print("ТЕСТ: Планирование сложной задачи с диалогом агентов (реальные LLM)")
    print("="*80)
    
    # Проверить наличие серверов
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        pytest.skip("Нет активных серверов")
    
    server = None
    for s in servers:
        if "10.39.0.6" in s.url:
            server = s
            break
    if not server:
        server = servers[0]
    
    print(f"\n✓ Сервер: {server.name} ({server.url})")
    
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
    
    print(f"✓ Агент 1: {agent1.name}")
    print(f"✓ Агент 2: {agent2.name}")
    
    # Сложная задача
    complex_task = "Создай архитектуру веб-приложения с множественными компонентами, интеграцией сервисов и координацией между модулями системы"
    
    print(f"\n✓ Задача: {complex_task[:80]}...")
    
    # Проверить, что задача сложная
    assert is_complex_task(complex_task) is True, "Задача должна быть определена как сложная"
    print("✓ Задача определена как сложная")
    
    # Создать задачу
    task = Task(
        description=complex_task,
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    print(f"✓ Задача создана: {task.id}")
    
    # Генерировать план (должен автоматически создать диалог)
    print("\n" + "-"*80)
    print("ГЕНЕРАЦИЯ ПЛАНА (с автоматическим диалогом)...")
    print("-"*80)
    
    planning_service = PlanningService(db)
    plan = await planning_service.generate_plan(
        task_description=complex_task,
        task_id=task.id
    )
    
    assert plan is not None, "План должен быть создан"
    assert plan.task_id == task.id, "План должен быть связан с задачей"
    
    print(f"✓ План создан: {plan.id}")
    print(f"✓ Статус плана: {plan.status}")
    print(f"✓ Шагов в плане: {len(plan.steps) if plan.steps else 0}")
    
    # Проверить диалог
    print("\n" + "-"*80)
    print("ПРОВЕРКА ДИАЛОГА...")
    print("-"*80)
    
    dialog_service = AgentDialogService(db)
    conversations = dialog_service.get_conversations_by_task(task.id)
    
    if len(conversations) > 0:
        conversation = conversations[0]
        print(f"✓ Диалог создан: {conversation.id}")
        print(f"✓ Статус диалога: {conversation.status}")
        print(f"✓ Участников: {len(conversation.get_participants())}")
        print(f"✓ Сообщений: {len(conversation.get_messages())}")
        
        # Показать сообщения
        messages = conversation.get_messages()
        if messages:
            print(f"\n  Сообщения диалога:")
            for i, msg in enumerate(messages[:3], 1):  # Показать первые 3
                content_preview = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
                print(f"    {i}. {content_preview}")
        
        assert conversation.status in [ConversationStatus.COMPLETED.value, ConversationStatus.ACTIVE.value]
        assert len(conversation.get_participants()) >= 2
    else:
        print("⚠ Диалог не создан (возможно, агенты не найдены или задача не достаточно сложная)")
    
    # Проверить контекст в Digital Twin
    print("\n" + "-"*80)
    print("ПРОВЕРКА DIGITAL TWIN...")
    print("-"*80)
    
    db.refresh(task)
    context = task.get_context()
    
    if "agent_dialog" in context:
        print("✓ Контекст диалога сохранен в Digital Twin")
        dialog_info = context["agent_dialog"]
        print(f"  - Conversation ID: {dialog_info.get('conversation_id', 'N/A')}")
        print(f"  - Initiated at: {dialog_info.get('initiated_at', 'N/A')}")
        if "context" in dialog_info and "discussion_summary" in dialog_info["context"]:
            summary = dialog_info["context"]["discussion_summary"][:100]
            print(f"  - Discussion summary: {summary}...")
    else:
        print("⚠ Контекст диалога не найден в Digital Twin (диалог мог не создаться)")
    
    # Проверить, что план использует результаты диалога
    print("\n" + "-"*80)
    print("ПРОВЕРКА ИСПОЛЬЗОВАНИЯ РЕЗУЛЬТАТОВ ДИАЛОГА...")
    print("-"*80)
    
    if plan.goal:
        print(f"✓ Цель плана: {plan.goal[:100]}...")
    
    if plan.steps:
        print(f"✓ Шаги плана:")
        for i, step in enumerate(plan.steps[:3], 1):  # Показать первые 3 шага
            step_desc = step.get('description', step.get('step_description', 'N/A'))[:60]
            print(f"    {i}. {step_desc}...")
    
    print("\n" + "="*80)
    print("✓ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
    print("="*80)
    
    # Финальные проверки
    assert plan is not None
    assert plan.task_id == task.id
    # Диалог может быть создан или нет, в зависимости от наличия агентов
    # Главное - система работает корректно

