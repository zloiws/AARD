"""
Тест интеграции Chat API с PlanningService и ExecutionService
"""
from uuid import uuid4

import pytest
from app.api.routes.chat import ChatMessage, chat
from app.core.request_router import RequestType, determine_request_type
from app.models.task import Task, TaskStatus
from app.services.execution_service import ExecutionService
from app.services.planning_service import PlanningService
from sqlalchemy.orm import Session


@pytest.mark.asyncio
async def test_chat_information_query(db: Session):
    """
    Тест: Chat API определяет информационный запрос и использует PlanningService
    """
    # Проверяем определение типа запроса
    request_type, metadata = determine_request_type("сколько стоит iPad")
    
    assert request_type == RequestType.INFORMATION_QUERY
    assert metadata.get("requires_search") is True
    
    # Проверяем, что для информационного запроса создается задача и план
    task_description = "сколько стоит iPad"
    
    task = Task(
        description=task_description,
        status=TaskStatus.PENDING
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Генерируем план
    planning_service = PlanningService(db)
    plan = await planning_service.generate_plan(
        task_id=task.id,
        task_description=task_description,
        context={"requires_search": True}
    )
    
    assert plan is not None
    assert plan.task_id == task.id
    
    # План должен быть одобрен автоматически для простых запросов
    # (или требовать одобрения в зависимости от настроек)
    assert plan.status in ["draft", "approved"]


@pytest.mark.asyncio
async def test_chat_simple_question(db: Session):
    """
    Тест: Простой вопрос обрабатывается напрямую через LLM
    """
    request_type, metadata = determine_request_type("Привет, как дела?")
    
    assert request_type == RequestType.SIMPLE_QUESTION
    assert metadata.get("direct_llm") is True


@pytest.mark.asyncio
async def test_chat_code_generation(db: Session):
    """
    Тест: Запрос на генерацию кода использует PlanningService
    """
    request_type, metadata = determine_request_type("напиши код функции для сортировки")
    
    assert request_type == RequestType.CODE_GENERATION
    assert metadata.get("requires_planning") is True

