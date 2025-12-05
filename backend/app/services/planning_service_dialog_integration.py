"""
Методы интеграции диалогов в PlanningService
Вынесены в отдельный файл для читаемости
"""
from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID
from datetime import datetime
import asyncio

from sqlalchemy.orm import Session

from app.services.agent_dialog_service import AgentDialogService
from app.services.agent_service import AgentService
from app.models.agent import Agent, AgentStatus
from app.models.agent_conversation import ConversationStatus, MessageRole
from app.core.ollama_client import OllamaClient, TaskType
from app.core.model_selector import ModelSelector
from app.services.ollama_service import OllamaService
from app.core.logging_config import LoggingConfig
from app.core.config import get_settings

logger = LoggingConfig.get_logger(__name__)
settings = get_settings()


def is_complex_task(
    task_description: str,
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Определить, является ли задача сложной и требует ли диалога между агентами
    
    Критерии сложности:
    - Длина описания > 200 символов
    - Содержит ключевые слова сложности
    - Требует множественных компетенций
    - Явно указано в context["requires_dialog"] = True
    
    Args:
        task_description: Описание задачи
        context: Дополнительный контекст
        
    Returns:
        True если задача сложная и требует диалога
    """
    # Явное указание в контексте
    if context and context.get("requires_dialog") is True:
        return True
    
    # Длина описания
    if len(task_description) > 200:
        return True
    
    # Ключевые слова сложности
    complexity_keywords = [
        "сложн", "complex", "multiple", "несколько", "множеств",
        "архитектур", "architecture", "систем", "system",
        "интеграц", "integration", "координац", "coordination",
        "совместн", "collaborative", "обсужд", "discuss"
    ]
    
    task_lower = task_description.lower()
    keyword_count = sum(1 for keyword in complexity_keywords if keyword in task_lower)
    
    if keyword_count >= 2:
        return True
    
    # Требует множественных компетенций
    required_capabilities = []
    if any(word in task_lower for word in ["code", "program", "script", "function", "код", "программ"]):
        required_capabilities.append("code")
    if any(word in task_lower for word in ["plan", "strategy", "design", "план", "стратег", "дизайн"]):
        required_capabilities.append("planning")
    if any(word in task_lower for word in ["analyze", "review", "test", "анализ", "проверк", "тест"]):
        required_capabilities.append("analysis")
    
    if len(required_capabilities) >= 2:
        return True
    
    return False


async def initiate_agent_dialog_for_planning(
    db: Session,
    task_description: str,
    task_id: Optional[UUID] = None,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[UUID], Dict[str, Any]]:
    """
    Инициировать диалог между агентами для обсуждения сложной задачи
    
    Args:
        db: Database session
        task_description: Описание задачи
        task_id: ID задачи
        context: Дополнительный контекст
        
    Returns:
        Tuple of (conversation_id, dialog_context)
        conversation_id может быть None если диалог не удалось создать
    """
    dialog_service = AgentDialogService(db)
    agent_service = AgentService(db)
    
    try:
        # Выбрать агентов для диалога
        # Нужны агенты с разными компетенциями
        agents = []
        
        # Агент-планировщик
        planner_agent = agent_service.select_agent_for_task(
            required_capabilities=["planning", "reasoning"]
        )
        if planner_agent:
            agents.append(planner_agent)
        
        # Агент-разработчик (если задача требует кода)
        task_lower = task_description.lower()
        if any(word in task_lower for word in ["code", "program", "script", "function", "код"]):
            developer_agent = agent_service.select_agent_for_task(
                required_capabilities=["code_generation"]
            )
            if developer_agent and developer_agent.id not in [a.id for a in agents]:
                agents.append(developer_agent)
        
        # Если не нашли агентов, создадим временных или используем существующих активных
        if len(agents) < 2:
            # Получить активных агентов
            active_agents = db.query(Agent).filter(
                Agent.status == AgentStatus.ACTIVE.value
            ).limit(2).all()
            
            for agent in active_agents:
                if agent.id not in [a.id for a in agents]:
                    agents.append(agent)
                    if len(agents) >= 2:
                        break
        
        if len(agents) < 2:
            logger.warning("Не удалось найти достаточно агентов для диалога")
            return None, {}
        
        # Создать диалог
        conversation = dialog_service.create_conversation(
            participant_ids=[agent.id for agent in agents],
            goal=f"Обсудить и спланировать решение задачи: {task_description[:200]}",
            title=f"Диалог о планировании задачи",
            task_id=task_id,
            initial_context={
                "task_description": task_description,
                "context": context or {}
            }
        )
        
        logger.info(
            f"Создан диалог для планирования: {conversation.id}",
            extra={
                "conversation_id": str(conversation.id),
                "task_id": str(task_id),
                "participants": [str(a.id) for a in agents]
            }
        )
        
        # Провести диалог между агентами через LLM
        dialog_context = await conduct_agent_dialog(
            db=db,
            conversation_id=conversation.id,
            agents=agents,
            task_description=task_description,
            context=context
        )
        
        return conversation.id, dialog_context
        
    except Exception as e:
        logger.error(
            f"Ошибка при создании диалога для планирования: {e}",
            exc_info=True,
            extra={"task_id": str(task_id)}
        )
        return None, {}


async def conduct_agent_dialog(
    db: Session,
    conversation_id: UUID,
    agents: List[Agent],
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    max_turns: int = 3
) -> Dict[str, Any]:
    """
    Провести диалог между агентами через реальные LLM вызовы
    
    Args:
        db: Database session
        conversation_id: ID диалога
        agents: Список агентов-участников
        task_description: Описание задачи
        context: Дополнительный контекст
        max_turns: Максимальное количество раундов диалога
        
    Returns:
        Контекст диалога с результатами обсуждения
    """
    dialog_service = AgentDialogService(db)
    ollama_client = OllamaClient()
    model_selector = ModelSelector(db)
    
    # Получить сервер и модель
    servers = OllamaService.get_all_active_servers(db)
    if not servers:
        logger.warning("Нет активных серверов для диалога")
        return {}
    
    server = servers[0]  # Использовать первый активный сервер
    planning_model = model_selector.get_planning_model(server=server)
    
    if not planning_model:
        logger.warning("Не удалось выбрать модель для диалога")
        return {}
    
    server_url = server.get_api_url()
    discussion_summary = []
    
    try:
        # Первый агент начинает диалог
        agent1 = agents[0]
        agent1_prompt = f"""Ты агент-{agent1.capabilities[0] if agent1.capabilities else 'планировщик'}. 

Задача: {task_description}

Начни обсуждение задачи. Предложи подход к решению. Ответ должен быть кратким (2-3 предложения)."""
        
        response1 = await asyncio.wait_for(
            ollama_client.generate(
                prompt=agent1_prompt,
                task_type=TaskType.PLANNING,
                model=planning_model.model_name,
                server_url=server_url,
                num_predict=200
            ),
            timeout=30
        )
        
        message1_content = response1.response.strip() if hasattr(response1, 'response') else str(response1).strip()
        dialog_service.add_message(
            conversation_id=conversation_id,
            agent_id=agent1.id,
            content=message1_content,
            role=MessageRole.AGENT
        )
        discussion_summary.append(f"{agent1.name}: {message1_content}")
        
        # Второй агент отвечает
        if len(agents) > 1:
            agent2 = agents[1]
            conversation = dialog_service.get_conversation(conversation_id)
            messages = conversation.get_messages()
            
            agent2_prompt = f"""Ты агент-{agent2.capabilities[0] if agent2.capabilities else 'разработчик'}.

Задача: {task_description}

История обсуждения:
{chr(10).join([f"{msg['agent_id'][:8]}: {msg['content']}" for msg in messages[-2:]])}

Ответь на предложение первого агента. Предложи свой подход или дополнения. Ответ должен быть кратким (2-3 предложения)."""
            
            response2 = await asyncio.wait_for(
                ollama_client.generate(
                    prompt=agent2_prompt,
                    task_type=TaskType.PLANNING,
                    model=planning_model.model_name,
                    server_url=server_url,
                    num_predict=200
                ),
                timeout=30
            )
            
            message2_content = response2.response.strip() if hasattr(response2, 'response') else str(response2).strip()
            dialog_service.add_message(
                conversation_id=conversation_id,
                agent_id=agent2.id,
                content=message2_content,
                role=MessageRole.AGENT
            )
            discussion_summary.append(f"{agent2.name}: {message2_content}")
        
        # Обновить контекст диалога с результатами
        dialog_service.update_context(
            conversation_id=conversation_id,
            updates={
                "discussion_summary": " | ".join(discussion_summary),
                "agreed_approach": "Агенты обсудили подход к решению",
                "completed_at": datetime.utcnow().isoformat()
            }
        )
        
        # Завершить диалог
        dialog_service.complete_conversation(
            conversation_id=conversation_id,
            success=True,
            result={
                "discussion_summary": " | ".join(discussion_summary),
                "participants": [str(a.id) for a in agents]
            }
        )
        
        return {
            "discussion_summary": " | ".join(discussion_summary),
            "participants": [str(a.id) for a in agents],
            "messages_count": len(dialog_service.get_conversation(conversation_id).get_messages())
        }
        
    except asyncio.TimeoutError:
        logger.warning(f"Таймаут диалога для conversation {conversation_id}")
        return {
            "discussion_summary": " | ".join(discussion_summary) if discussion_summary else "Диалог не завершен",
            "error": "timeout"
        }
    except Exception as e:
        logger.error(f"Ошибка при проведении диалога: {e}", exc_info=True)
        return {
            "discussion_summary": " | ".join(discussion_summary) if discussion_summary else "Ошибка диалога",
            "error": str(e)
        }

