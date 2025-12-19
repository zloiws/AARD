"""
Integration tests for Agent Dialogs (Phase 8.1)
Tests the complete dialog system between agents
"""
import asyncio
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from app.models.agent import Agent, AgentStatus
from app.models.agent_conversation import (AgentConversation,
                                           ConversationStatus, MessageRole)
from app.models.task import Task, TaskStatus
from app.services.agent_dialog_service import AgentDialogService
from app.services.agent_service import AgentService


@pytest.mark.asyncio
async def test_complete_dialog_cycle(db):
    """
    Полный цикл диалога между агентами
    
    Проверяет:
    1. Создание диалога
    2. Добавление сообщений от разных агентов
    3. Управление контекстом
    4. Проверка завершения
    5. Завершение диалога
    """
    # Создать агентов
    agent_service = AgentService(db)
    agent1 = agent_service.create_agent(
        name=f"Dialog Agent 1 {uuid4()}",
        description="First agent in dialog",
        capabilities=["planning", "reasoning"]
    )
    # Активировать агента
    agent1.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent1)
    
    agent2 = agent_service.create_agent(
        name=f"Dialog Agent 2 {uuid4()}",
        description="Second agent in dialog",
        capabilities=["code_generation"]
    )
    # Активировать агента
    agent2.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent2)
    
    # Создать сервис диалогов
    dialog_service = AgentDialogService(db)
    
    # 1. Создать диалог
    conversation = dialog_service.create_conversation(
        participant_ids=[agent1.id, agent2.id],
        goal="Обсудить и спланировать решение задачи",
        title="Планирование решения",
        initial_context={"task": "Создать веб-приложение"}
    )
    
    assert conversation.id is not None
    assert conversation.status == ConversationStatus.INITIATED.value
    assert len(conversation.get_participants()) == 2
    
    # 2. Агент 1 начинает диалог
    message1 = dialog_service.add_message(
        conversation_id=conversation.id,
        agent_id=agent1.id,
        content="Привет! Мне нужна помощь с планированием задачи.",
        role=MessageRole.AGENT
    )
    
    db.refresh(conversation)
    assert conversation.status == ConversationStatus.ACTIVE.value
    assert len(conversation.get_messages()) == 1
    
    # 3. Агент 2 отвечает
    message2 = dialog_service.add_message(
        conversation_id=conversation.id,
        agent_id=agent2.id,
        content="Конечно! Расскажи подробнее о задаче.",
        role=MessageRole.AGENT
    )
    
    db.refresh(conversation)
    assert len(conversation.get_messages()) == 2
    
    # 4. Обновить контекст с промежуточными результатами
    dialog_service.update_context(
        conversation_id=conversation.id,
        updates={
            "discussed_points": ["Архитектура", "Технологии"],
            "agreed_approach": "Использовать Python и FastAPI"
        }
    )
    
    db.refresh(conversation)
    context = conversation.get_context()
    assert "discussed_points" in context
    assert "agreed_approach" in context
    
    # 5. Продолжить диалог
    message3 = dialog_service.add_message(
        conversation_id=conversation.id,
        agent_id=agent1.id,
        content="Отлично! Давай составим план действий.",
        role=MessageRole.AGENT
    )
    
    message4 = dialog_service.add_message(
        conversation_id=conversation.id,
        agent_id=agent2.id,
        content="Согласен. Начнем с создания структуры проекта.",
        role=MessageRole.AGENT
    )
    
    db.refresh(conversation)
    assert len(conversation.get_messages()) == 4
    
    # 6. Проверить завершение (еще не завершен)
    assert dialog_service.is_conversation_complete(
        conversation.id,
        check_conditions={"min_messages": 5}
    ) is False
    
    # 7. Добавить еще сообщение для достижения минимума
    message5 = dialog_service.add_message(
        conversation_id=conversation.id,
        agent_id=agent1.id,
        content="Хорошо, план готов. Завершаем диалог.",
        role=MessageRole.AGENT
    )
    
    # 8. Завершить диалог
    completed = dialog_service.complete_conversation(
        conversation_id=conversation.id,
        success=True,
        result={
            "plan": "Создать структуру проекта, настроить окружение, реализовать API",
            "technologies": ["Python", "FastAPI", "PostgreSQL"]
        }
    )
    
    assert completed.status == ConversationStatus.COMPLETED.value
    assert completed.completed_at is not None
    
    # Проверить результат в контексте
    final_context = completed.get_context()
    assert "result" in final_context
    assert final_context["result"]["plan"] is not None


@pytest.mark.asyncio
async def test_dialog_with_task(db):
    """Тест диалога, связанного с задачей"""
    # Создать задачу
    task = Task(
        description="Сложная задача, требующая обсуждения",
        status=TaskStatus.PENDING.value
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Создать агентов
    agent_service = AgentService(db)
    agent1 = agent_service.create_agent(name=f"Task Agent 1 {uuid4()}")
    agent1.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent1)
    
    agent2 = agent_service.create_agent(name=f"Task Agent 2 {uuid4()}")
    agent2.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent2)
    
    # Создать диалог для задачи
    dialog_service = AgentDialogService(db)
    conversation = dialog_service.create_conversation(
        participant_ids=[agent1.id, agent2.id],
        goal="Обсудить подход к решению задачи",
        task_id=task.id
    )
    
    assert conversation.task_id == task.id
    
    # Получить диалоги задачи
    task_conversations = dialog_service.get_conversations_by_task(task.id)
    assert len(task_conversations) == 1
    assert task_conversations[0].id == conversation.id


@pytest.mark.asyncio
async def test_dialog_pause_and_resume(db):
    """Тест паузы и возобновления диалога"""
    agent_service = AgentService(db)
    agent1 = agent_service.create_agent(name=f"Pause Agent 1 {uuid4()}")
    agent1.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent1)
    
    agent2 = agent_service.create_agent(name=f"Pause Agent 2 {uuid4()}")
    agent2.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent2)
    
    dialog_service = AgentDialogService(db)
    conversation = dialog_service.create_conversation(
        participant_ids=[agent1.id, agent2.id]
    )
    
    # Добавить сообщение (активирует диалог)
    dialog_service.add_message(
        conversation_id=conversation.id,
        agent_id=agent1.id,
        content="Начинаем диалог"
    )
    
    db.refresh(conversation)
    assert conversation.status == ConversationStatus.ACTIVE.value
    
    # Приостановить
    paused = dialog_service.pause_conversation(conversation.id)
    assert paused.status == ConversationStatus.PAUSED.value
    
    # Возобновить
    resumed = dialog_service.resume_conversation(conversation.id)
    assert resumed.status == ConversationStatus.ACTIVE.value


@pytest.mark.asyncio
async def test_dialog_max_messages_completion(db):
    """Тест завершения диалога по достижению максимума сообщений"""
    agent_service = AgentService(db)
    agent1 = agent_service.create_agent(name=f"Max Agent 1 {uuid4()}")
    agent1.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent1)
    
    agent2 = agent_service.create_agent(name=f"Max Agent 2 {uuid4()}")
    agent2.status = AgentStatus.ACTIVE.value
    db.commit()
    db.refresh(agent2)
    
    dialog_service = AgentDialogService(db)
    conversation = dialog_service.create_conversation(
        participant_ids=[agent1.id, agent2.id]
    )
    
    # Добавить сообщения до лимита
    max_messages = 5
    for i in range(max_messages):
        dialog_service.add_message(
            conversation_id=conversation.id,
            agent_id=agent1.id if i % 2 == 0 else agent2.id,
            content=f"Message {i + 1}"
        )
    
    # Проверить завершение
    db.refresh(conversation)
    is_complete = dialog_service.is_conversation_complete(
        conversation.id,
        check_conditions={"max_messages": max_messages}
    )
    
    assert is_complete is True


@pytest.mark.asyncio
async def test_dialog_multiple_agents(db):
    """Тест диалога с несколькими агентами (3+)"""
    agent_service = AgentService(db)
    agents = []
    for i in range(3):
        agent = agent_service.create_agent(name=f"Multi Agent {i+1} {uuid4()}")
        agent.status = AgentStatus.ACTIVE.value
        db.commit()
        db.refresh(agent)
        agents.append(agent)
    
    dialog_service = AgentDialogService(db)
    conversation = dialog_service.create_conversation(
        participant_ids=[agent.id for agent in agents],
        goal="Групповое обсуждение"
    )
    
    assert len(conversation.get_participants()) == 3
    
    # Каждый агент отправляет сообщение
    for i, agent in enumerate(agents):
        dialog_service.add_message(
            conversation_id=conversation.id,
            agent_id=agent.id,
            content=f"Сообщение от агента {i+1}"
        )
    
    db.refresh(conversation)
    assert len(conversation.get_messages()) == 3

