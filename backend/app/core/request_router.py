"""
Request Router - определяет тип запроса и маршрутизирует его
"""
from typing import Dict, Any, Optional, Tuple
from enum import Enum

from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


class RequestType(str, Enum):
    """Тип запроса пользователя"""
    SIMPLE_QUESTION = "simple_question"  # Простой вопрос - прямой LLM ответ
    INFORMATION_QUERY = "information_query"  # Информационный запрос - нужен поиск
    CODE_GENERATION = "code_generation"  # Генерация кода - нужен PlanningService
    COMPLEX_TASK = "complex_task"  # Сложная задача - нужен PlanningService + ExecutionService
    PLANNING_ONLY = "planning_only"  # Только планирование без выполнения


def determine_request_type(message: str, task_type: Optional[str] = None) -> Tuple[RequestType, Dict[str, Any]]:
    """
    Определить тип запроса и необходимые действия
    
    Args:
        message: Сообщение пользователя
        task_type: Явно указанный тип задачи
        
    Returns:
        Tuple of (RequestType, metadata)
    """
    message_lower = message.lower()
    
    # Если явно указан тип задачи
    if task_type:
        if task_type in ["code_generation", "code_analysis"]:
            return RequestType.CODE_GENERATION, {"reason": "explicit_code_task"}
        if task_type == "planning":
            return RequestType.PLANNING_ONLY, {"reason": "explicit_planning_task"}
    
    # Информационные запросы (нужен поиск в интернете)
    information_keywords = [
        "сколько стоит", "цена", "стоимость", "price", "cost",
        "когда", "when", "где", "where", "как найти", "how to find",
        "актуальн", "current", "latest", "новост", "news",
        "курс", "exchange rate", "погода", "weather",
        "расписани", "schedule", "время работы", "working hours"
    ]
    
    if any(keyword in message_lower for keyword in information_keywords):
        return RequestType.INFORMATION_QUERY, {
            "reason": "information_keywords",
            "requires_search": True
        }
    
    # Запросы на генерацию кода
    code_keywords = [
        "напиши код", "создай функцию", "напиши программу",
        "write code", "create function", "generate code",
        "реализуй", "implement", "сделай скрипт", "make script"
    ]
    
    if any(keyword in message_lower for keyword in code_keywords):
        return RequestType.CODE_GENERATION, {
            "reason": "code_keywords",
            "requires_planning": True
        }
    
    # Сложные задачи (требуют планирования и выполнения)
    complex_keywords = [
        "создай систему", "разработай", "построй", "build system",
        "сделай проект", "create project", "автоматизируй", "automate",
        "настрой", "configure", "установи", "install", "setup"
    ]
    
    if any(keyword in message_lower for keyword in complex_keywords):
        return RequestType.COMPLEX_TASK, {
            "reason": "complex_keywords",
            "requires_planning": True,
            "requires_execution": True
        }
    
    # Длинные запросы (> 200 символов) - вероятно сложная задача
    if len(message) > 200:
        return RequestType.COMPLEX_TASK, {
            "reason": "long_message",
            "requires_planning": True
        }
    
    # По умолчанию - простой вопрос
    return RequestType.SIMPLE_QUESTION, {
        "reason": "default",
        "direct_llm": True
    }

