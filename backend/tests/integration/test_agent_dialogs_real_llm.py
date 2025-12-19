"""
Real LLM tests for Agent Dialogs
Тесты диалогов между агентами с реальными LLM вызовами
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app.core.config import get_settings
from app.core.model_selector import ModelSelector
from app.core.ollama_client import OllamaClient, TaskType
from app.models.agent import Agent, AgentStatus
from app.models.agent_conversation import (AgentConversation,
                                           ConversationStatus, MessageRole)
from app.models.task import Task, TaskStatus
from app.services.agent_dialog_service import AgentDialogService
from app.services.agent_service import AgentService
from app.services.ollama_service import OllamaService

# Настройка отдельного логирования для этого теста
TEST_LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "tests"
TEST_LOG_DIR.mkdir(parents=True, exist_ok=True)
TEST_LOG_FILE = TEST_LOG_DIR / f"agent_dialogs_real_llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Настройка логгера
test_logger = logging.getLogger("agent_dialogs_llm_test")
test_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(TEST_LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
test_logger.addHandler(file_handler)

# Таймауты для ограниченного железа
TIMEOUTS = {
    "llm_call": 30,  # 30 секунд на LLM вызов
    "dialog_message": 20,  # 20 секунд на генерацию сообщения агентом
    "full_dialog": 120,  # 2 минуты на полный диалог
}

settings = get_settings()


class TestStage:
    """Контекстный менеджер для структурированного логирования этапов теста"""
    
    def __init__(self, stage_name: str, logger: logging.Logger):
        self.stage_name = stage_name
        self.logger = logger
        self.start_time = None
        self.details = []
        self.warnings = []
        self.errors = []
        self.success = False
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info("\n" + "="*100)
        self.logger.info(f"ЭТАП: {self.stage_name}")
        self.logger.info("="*100)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        self.logger.info("\n" + "-"*100)
        status = "✓ УСПЕШНО" if self.success and not self.errors else "✗ ОШИБКА"
        self.logger.info(f"РЕЗУЛЬТАТ ЭТАПА '{self.stage_name}': {status}")
        self.logger.info(f"Длительность: {duration:.2f} сек")
        
        if self.details:
            self.logger.info("Детали:")
            for detail in self.details:
                self.logger.info(f"  {detail}")
        
        if self.warnings:
            self.logger.info(f"Предупреждения ({len(self.warnings)}):")
            for warning in self.warnings:
                self.logger.warning(f"  - {warning}")
        
        if self.errors:
            self.logger.error(f"Ошибки ({len(self.errors)}):")
            for error in self.errors:
                self.logger.error(f"  ✗ {error}")
        
        self.logger.info("-"*100)
        return False  # Не подавляем исключения
    
    def add_detail(self, key: str, value: str):
        """Добавить деталь"""
        self.details.append(f"{key}: {value}")
        self.logger.debug(f"  {key}: {value}")
    
    def add_warning(self, message: str):
        """Добавить предупреждение"""
        self.warnings.append(message)
        self.logger.warning(f"  ⚠ {message}")
    
    def add_error(self, message: str):
        """Добавить ошибку"""
        self.errors.append(message)
        self.logger.error(f"  ✗ {message}")
    
    def set_success(self, success: bool = True):
        """Установить статус успешности"""
        self.success = success


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(300)  # Общий таймаут: 5 минут
async def test_real_agent_dialog_with_llm(db):
    """
    Реальный тест диалога между агентами с использованием LLM
    
    Проверяет:
    1. Создание агентов и диалога
    2. Генерацию сообщений через реальные LLM
    3. Обмен сообщениями между агентами
    4. Управление контекстом диалога
    5. Завершение диалога
    """
    
    test_logger.info("\n" + "#"*100)
    test_logger.info("НАЧАЛО ТЕСТА: Реальный диалог между агентами с LLM")
    test_logger.info(f"Лог файл: {TEST_LOG_FILE}")
    test_logger.info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    test_logger.info(f"⚡ РЕЖИМ: Реальные LLM вызовы (ограниченное железо)")
    test_logger.info(f"⏱️  Таймауты: LLM={TIMEOUTS['llm_call']}с, Сообщение={TIMEOUTS['dialog_message']}с, Диалог={TIMEOUTS['full_dialog']}с")
    test_logger.info("#"*100 + "\n")
    
    overall_start = datetime.now()
    dialog_goal = "Обсудить и решить простую задачу: написать функцию на Python, которая возвращает 'Привет, мир!'"
    
    try:
        # ========================================================================
        # ЭТАП 1: Инициализация и проверка окружения
        # ========================================================================
        with TestStage("1. Инициализация и проверка окружения", test_logger) as stage:
            # Проверить наличие активных серверов
            active_servers = OllamaService.get_all_active_servers(db)
            
            if not active_servers:
                stage.add_error("Нет активных Ollama серверов")
                stage.set_success(False)
                pytest.skip("Нет активных Ollama серверов для теста")
            
            # Использовать сервер 10.39.0.6 если доступен
            target_server = None
            for server in active_servers:
                if "10.39.0.6" in server.url:
                    target_server = server
                    break
            
            if not target_server:
                target_server = active_servers[0]
            
            stage.add_detail("Выбранный сервер", f"{target_server.name} ({target_server.url})")
            
            # Проверить модели на сервере
            models = OllamaService.get_models_for_server(db, str(target_server.id))
            if not models:
                stage.add_error("Нет моделей на сервере")
                stage.set_success(False)
                pytest.skip("Нет моделей на сервере")
            
            # Выбрать модель (исключить embedding модели)
            model_selector = ModelSelector(db)
            planning_model = model_selector.get_planning_model(server=target_server)
            
            if not planning_model:
                stage.add_error("Не удалось выбрать модель для планирования")
                stage.set_success(False)
                pytest.skip("Нет подходящей модели")
            
            stage.add_detail("Модель планирования", f"{planning_model.model_name}")
            stage.add_detail("Сервер", f"{target_server.url}")
            stage.set_success(True)
        
        # ========================================================================
        # ЭТАП 2: Создание агентов
        # ========================================================================
        with TestStage("2. Создание агентов", test_logger) as stage:
            agent_service = AgentService(db)
            
            # Создать агента-планировщика
            agent1 = agent_service.create_agent(
                name=f"Planner Agent {uuid4()}",
                description="Агент для планирования и рассуждений",
                capabilities=["planning", "reasoning"],
                model_preference=planning_model.model_name
            )
            agent1.status = AgentStatus.ACTIVE.value
            db.commit()
            db.refresh(agent1)
            
            # Создать агента-разработчика
            agent2 = agent_service.create_agent(
                name=f"Developer Agent {uuid4()}",
                description="Агент для генерации кода",
                capabilities=["code_generation"],
                model_preference=planning_model.model_name  # Используем ту же модель для простоты
            )
            agent2.status = AgentStatus.ACTIVE.value
            db.commit()
            db.refresh(agent2)
            
            stage.add_detail("Агент 1", f"{agent1.name} ({agent1.id})")
            stage.add_detail("Агент 2", f"{agent2.name} ({agent2.id})")
            stage.set_success(True)
        
        # ========================================================================
        # ЭТАП 3: Создание диалога
        # ========================================================================
        with TestStage("3. Создание диалога", test_logger) as stage:
            dialog_service = AgentDialogService(db)
            
            conversation = dialog_service.create_conversation(
                participant_ids=[agent1.id, agent2.id],
                goal=dialog_goal,
                title="Диалог о решении задачи",
                initial_context={"task": "Написать функцию на Python"}
            )
            
            stage.add_detail("ID диалога", str(conversation.id))
            stage.add_detail("Цель", dialog_goal)
            stage.add_detail("Статус", conversation.status)
            stage.add_detail("Участников", str(len(conversation.get_participants())))
            stage.set_success(True)
        
        # ========================================================================
        # ЭТАП 4: Генерация сообщений через реальные LLM
        # ========================================================================
        with TestStage("4. Генерация сообщений через реальные LLM", test_logger) as stage:
            ollama_client = OllamaClient()
            server_url = target_server.get_api_url()
            
            # Агент 1 начинает диалог
            test_logger.info("\n🤖 АГЕНТ 1 генерирует первое сообщение...")
            try:
                agent1_prompt = f"""Ты агент-планировщик. Твоя задача: {dialog_goal}

Начни диалог с агентом-разработчиком. Напиши короткое приветствие и предложи обсудить задачу.
Ответ должен быть кратким (1-2 предложения)."""
                
                response1 = await asyncio.wait_for(
                    ollama_client.generate(
                        prompt=agent1_prompt,
                        task_type=TaskType.PLANNING,
                        model=planning_model.model_name,
                        server_url=server_url,
                        use_cache=False  # Отключить кэш для реальных тестов
                    ),
                    timeout=TIMEOUTS["llm_call"]
                )
                
                agent1_message = response1.response.strip() if hasattr(response1, 'response') else str(response1).strip()
                test_logger.info(f"  ✓ Сообщение от Агента 1: {agent1_message[:100]}...")
                
                # Добавить сообщение в диалог
                message1 = dialog_service.add_message(
                    conversation_id=conversation.id,
                    agent_id=agent1.id,
                    content=agent1_message,
                    role=MessageRole.AGENT
                )
                
                stage.add_detail("Сообщение 1 (Агент 1)", agent1_message[:80] + "..." if len(agent1_message) > 80 else agent1_message)
                
            except asyncio.TimeoutError:
                stage.add_error(f"Таймаут генерации сообщения Агента 1 ({TIMEOUTS['llm_call']} сек)")
                stage.set_success(False)
                raise
            except Exception as e:
                stage.add_error(f"Ошибка генерации сообщения Агента 1: {str(e)}")
                stage.set_success(False)
                raise
            
            # Агент 2 отвечает
            test_logger.info("\n🤖 АГЕНТ 2 генерирует ответ...")
            try:
                # Получить контекст диалога
                messages = conversation.get_messages()
                conversation_history = "\n".join([
                    f"Агент {msg['agent_id'][:8]}: {msg['content']}" 
                    for msg in messages
                ])
                
                agent2_prompt = f"""Ты агент-разработчик. Твоя задача: {dialog_goal}

История диалога:
{conversation_history}

Ответь на сообщение агента-планировщика. Предложи конкретный подход к решению задачи.
Ответ должен быть кратким (1-2 предложения)."""
                
                response2 = await asyncio.wait_for(
                    ollama_client.generate(
                        prompt=agent2_prompt,
                        task_type=TaskType.CODE_GENERATION,
                        model=planning_model.model_name,
                        server_url=server_url,
                        use_cache=False  # Отключить кэш для реальных тестов
                    ),
                    timeout=TIMEOUTS["llm_call"]
                )
                
                agent2_message = response2.response.strip() if hasattr(response2, 'response') else str(response2).strip()
                test_logger.info(f"  ✓ Сообщение от Агента 2: {agent2_message[:100]}...")
                
                # Добавить сообщение в диалог
                message2 = dialog_service.add_message(
                    conversation_id=conversation.id,
                    agent_id=agent2.id,
                    content=agent2_message,
                    role=MessageRole.AGENT
                )
                
                stage.add_detail("Сообщение 2 (Агент 2)", agent2_message[:80] + "..." if len(agent2_message) > 80 else agent2_message)
                
            except asyncio.TimeoutError:
                stage.add_error(f"Таймаут генерации сообщения Агента 2 ({TIMEOUTS['llm_call']} сек)")
                stage.set_success(False)
                raise
            except Exception as e:
                stage.add_error(f"Ошибка генерации сообщения Агента 2: {str(e)}")
                stage.set_success(False)
                raise
            
            # Обновить контекст с результатами обсуждения
            dialog_service.update_context(
                conversation_id=conversation.id,
                updates={
                    "discussed_approach": "Агенты обсудили подход к решению",
                    "messages_count": len(conversation.get_messages())
                }
            )
            
            db.refresh(conversation)
            stage.add_detail("Всего сообщений", str(len(conversation.get_messages())))
            stage.set_success(True)
        
        # ========================================================================
        # ЭТАП 5: Завершение диалога
        # ========================================================================
        with TestStage("5. Завершение диалога", test_logger) as stage:
            # Проверить завершение
            is_complete = dialog_service.is_conversation_complete(
                conversation.id,
                check_conditions={
                    "min_messages": 2,  # Минимум 2 сообщения для завершения
                    "max_messages": 10  # Максимум 10 сообщений
                }
            )
            
            if is_complete or len(conversation.get_messages()) >= 2:
                # Завершить диалог
                completed = dialog_service.complete_conversation(
                    conversation_id=conversation.id,
                    success=True,
                    result={
                        "outcome": "Диалог успешно завершен",
                        "messages_exchanged": len(conversation.get_messages()),
                        "goal": dialog_goal
                    }
                )
                
                stage.add_detail("Статус", completed.status)
                stage.add_detail("Сообщений обменяно", str(len(completed.get_messages())))
                stage.set_success(True)
            else:
                stage.add_warning("Диалог не достиг условий завершения")
                stage.set_success(True)  # Частичный успех
        
        # ========================================================================
        # ФИНАЛЬНЫЕ ПРОВЕРКИ
        # ========================================================================
        db.refresh(conversation)
        
        test_logger.info("\n" + "="*100)
        test_logger.info("📤 РЕЗУЛЬТАТ ДИАЛОГА:")
        test_logger.info("="*100)
        test_logger.info(f"  ✓ Диалог ID: {conversation.id}")
        test_logger.info(f"  ✓ Статус: {conversation.status}")
        test_logger.info(f"  ✓ Сообщений: {len(conversation.get_messages())}")
        test_logger.info(f"  ✓ Участников: {len(conversation.get_participants())}")
        
        # Показать сообщения
        messages = conversation.get_messages()
        test_logger.info(f"\n  Сообщения диалога:")
        for i, msg in enumerate(messages, 1):
            agent_name = "Агент 1" if UUID(msg['agent_id']) == agent1.id else "Агент 2"
            content_preview = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
            test_logger.info(f"    {i}. {agent_name}: {content_preview}")
        
        # Проверки согласованности
        assert conversation.id is not None, "Диалог должен иметь ID"
        assert len(conversation.get_participants()) == 2, "Должно быть 2 участника"
        assert len(messages) >= 2, "Должно быть минимум 2 сообщения"
        assert conversation.status in [ConversationStatus.ACTIVE.value, ConversationStatus.COMPLETED.value], "Диалог должен быть активен или завершен"
        
        test_logger.info("\n✓ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        
    except Exception as e:
        test_logger.error(f"\n✗ ТЕСТ ЗАВЕРШИЛСЯ С ОШИБКОЙ: {str(e)}", exc_info=True)
        raise
    
    finally:
        overall_duration = (datetime.now() - overall_start).total_seconds()
        test_logger.info("\n" + "#"*100)
        test_logger.info("ЗАВЕРШЕНИЕ ТЕСТА")
        test_logger.info(f"Общая длительность: {overall_duration:.2f} сек ({overall_duration/60:.1f} мин)")
        test_logger.info(f"Время завершения: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        test_logger.info(f"Лог файл: {TEST_LOG_FILE}")
        test_logger.info("#"*100 + "\n")


@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.timeout(300)
async def test_real_agent_dialog_multiturn_llm(db):
    """
    Реальный тест многоходового диалога между агентами с LLM
    
    Проверяет:
    1. Несколько раундов обмена сообщениями
    2. Использование контекста предыдущих сообщений
    3. Эволюцию диалога
    """
    
    test_logger.info("\n" + "#"*100)
    test_logger.info("НАЧАЛО ТЕСТА: Многоходовый диалог с LLM")
    test_logger.info(f"Лог файл: {TEST_LOG_FILE}")
    test_logger.info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    test_logger.info("#"*100 + "\n")
    
    overall_start = datetime.now()
    dialog_goal = "Обсудить архитектуру простого веб-приложения"
    
    try:
        # Инициализация
        active_servers = OllamaService.get_all_active_servers(db)
        if not active_servers:
            pytest.skip("Нет активных серверов")
        
        # Выбрать сервер 10.39.0.6
        target_server = None
        for server in active_servers:
            if "10.39.0.6" in server.url:
                target_server = server
                break
        if not target_server:
            target_server = active_servers[0]
        
        model_selector = ModelSelector(db)
        planning_model = model_selector.get_planning_model(server=target_server)
        if not planning_model:
            pytest.skip("Нет подходящей модели")
        
        # Создать агентов
        agent_service = AgentService(db)
        agent1 = agent_service.create_agent(
            name=f"Architect Agent {uuid4()}",
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
        
        # Создать диалог
        dialog_service = AgentDialogService(db)
        conversation = dialog_service.create_conversation(
            participant_ids=[agent1.id, agent2.id],
            goal=dialog_goal
        )
        
        ollama_client = OllamaClient()
        server_url = target_server.get_api_url()
        
        # Несколько раундов диалога
        max_turns = 3
        for turn in range(max_turns):
            test_logger.info(f"\n🔄 Раунд {turn + 1} из {max_turns}")
            
            # Получить текущую историю
            messages = conversation.get_messages()
            conversation_history = "\n".join([
                f"Раунд {i+1}: Агент {msg['agent_id'][:8]}: {msg['content'][:100]}" 
                for i, msg in enumerate(messages[-4:])  # Последние 4 сообщения для контекста
            ])
            
            # Определить, кто говорит (чередование)
            current_agent = agent1 if turn % 2 == 0 else agent2
            other_agent = agent2 if turn % 2 == 0 else agent1
            
            # Сгенерировать сообщение
            prompt = f"""Ты агент в диалоге. Цель диалога: {dialog_goal}

История диалога:
{conversation_history if conversation_history else "Диалог только начался"}

Твоя роль: {'архитектор' if current_agent.id == agent1.id else 'разработчик'}
Ответь кратко (1-2 предложения), продолжая обсуждение."""
            
            try:
                response = await asyncio.wait_for(
                    ollama_client.generate(
                        prompt=prompt,
                        task_type=TaskType.PLANNING,
                        model=planning_model.model_name,
                        server_url=server_url,
                        use_cache=False  # Отключить кэш для реальных тестов
                    ),
                    timeout=TIMEOUTS["llm_call"]
                )
                
                message_content = response.response.strip() if hasattr(response, 'response') else str(response).strip()
                
                # Добавить сообщение
                dialog_service.add_message(
                    conversation_id=conversation.id,
                    agent_id=current_agent.id,
                    content=message_content,
                    role=MessageRole.AGENT
                )
                
                test_logger.info(f"  ✓ {current_agent.name}: {message_content[:80]}...")
                
            except asyncio.TimeoutError:
                test_logger.warning(f"  ⚠ Таймаут в раунде {turn + 1}")
                break
            except Exception as e:
                test_logger.warning(f"  ⚠ Ошибка в раунде {turn + 1}: {e}")
                break
        
        # Завершить диалог
        db.refresh(conversation)
        final_messages = conversation.get_messages()
        
        test_logger.info(f"\n📊 ИТОГИ ДИАЛОГА:")
        test_logger.info(f"  ✓ Сообщений: {len(final_messages)}")
        test_logger.info(f"  ✓ Статус: {conversation.status}")
        
        assert len(final_messages) >= 2, "Должно быть минимум 2 сообщения"
        
        test_logger.info("\n✓ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        
    except Exception as e:
        test_logger.error(f"\n✗ ТЕСТ ЗАВЕРШИЛСЯ С ОШИБКОЙ: {str(e)}", exc_info=True)
        raise
    
    finally:
        overall_duration = (datetime.now() - overall_start).total_seconds()
        test_logger.info(f"\nОбщая длительность: {overall_duration:.2f} сек ({overall_duration/60:.1f} мин)")

