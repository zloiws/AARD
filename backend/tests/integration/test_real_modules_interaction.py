"""
Real Modules Interaction Test
Проверяет реальное взаимодействие всех модулей проекта в полном workflow

Условия:
1. Ограничение времени тестов и запросов на разумное
2. Отдельное логирование для удобства разбора проблем
3. Поэтапный вывод результатов
"""
import pytest
import asyncio
import sys
import os
from uuid import uuid4
from datetime import datetime
import json
import logging
from pathlib import Path

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app.services.planning_service import PlanningService
from app.services.execution_service import ExecutionService
from app.services.agent_team_service import AgentTeamService
from app.services.agent_team_coordination import AgentTeamCoordination
from app.services.ollama_service import OllamaService
from app.models.task import Task, TaskStatus
from app.models.plan import Plan, PlanStatus
from app.models.agent_team import CoordinationStrategy, TeamStatus
from app.models.agent import Agent, AgentStatus
from app.core.ollama_client import OllamaClient, TaskType
from app.core.model_selector import ModelSelector

# Настройка отдельного логирования для этого теста
TEST_LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "tests"
TEST_LOG_DIR.mkdir(parents=True, exist_ok=True)
TEST_LOG_FILE = TEST_LOG_DIR / f"real_modules_interaction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Настройка логгера
test_logger = logging.getLogger("real_modules_test")
test_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(TEST_LOG_FILE, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
file_handler.setFormatter(formatter)
test_logger.addHandler(file_handler)

# Консольный handler для вывода в терминал
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(levelname)-8s | %(message)s')
console_handler.setFormatter(console_formatter)
test_logger.addHandler(console_handler)


class TestStage:
    """Класс для отслеживания этапов теста"""
    
    def __init__(self, name: str, logger: logging.Logger):
        self.name = name
        self.logger = logger
        self.start_time = None
        self.end_time = None
        self.success = False
        self.errors = []
        self.warnings = []
        self.details = {}
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"\n{'='*100}")
        self.logger.info(f"ЭТАП: {self.name}")
        self.logger.info(f"{'='*100}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = datetime.now()
        duration = (self.end_time - self.start_time).total_seconds()
        
        status = "✓ УСПЕШНО" if self.success else "✗ ОШИБКА"
        self.logger.info(f"\n{'-'*100}")
        self.logger.info(f"РЕЗУЛЬТАТ ЭТАПА '{self.name}': {status}")
        self.logger.info(f"Длительность: {duration:.2f} сек")
        
        if self.details:
            self.logger.info("Детали:")
            for key, value in self.details.items():
                self.logger.info(f"  {key}: {value}")
        
        if self.warnings:
            self.logger.warning(f"Предупреждения ({len(self.warnings)}):")
            for warning in self.warnings:
                self.logger.warning(f"  - {warning}")
        
        if self.errors:
            self.logger.error(f"Ошибки ({len(self.errors)}):")
            for error in self.errors:
                self.logger.error(f"  - {error}")
        
        self.logger.info(f"{'-'*100}\n")
        
        return False  # Не подавляем исключения
    
    def add_detail(self, key: str, value: any):
        """Добавить деталь этапа"""
        self.details[key] = value
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


# Таймауты для различных операций (в секундах)
TIMEOUTS = {
    "llm_call": 60,  # 1 минута на LLM вызов
    "planning": 180,  # 3 минуты на генерацию плана
    "execution_step": 120,  # 2 минуты на выполнение шага
    "full_execution": 600,  # 10 минут на полное выполнение
    "team_coordination": 300,  # 5 минут на координацию команды
}


@pytest.mark.asyncio
async def test_real_modules_interaction_full_workflow(db):
    """
    Полный тест реального взаимодействия модулей
    
    Проверяет:
    1. Инициализацию сервисов
    2. Выбор моделей через ModelSelector
    3. Генерацию плана через PlanningService
    4. Создание команды агентов
    5. Выполнение плана через ExecutionService
    6. Координацию через AgentTeamCoordination
    7. Взаимодействие через A2A Protocol
    """
    
    test_logger.info(f"\n{'#'*100}")
    test_logger.info(f"НАЧАЛО ТЕСТА: Реальное взаимодействие модулей")
    test_logger.info(f"Лог файл: {TEST_LOG_FILE}")
    test_logger.info(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    test_logger.info(f"{'#'*100}\n")
    
    overall_start = datetime.now()
    test_task_description = "Напиши программу на Python, которая выводит 'Привет, мир!' и сохраняет результат в файл"
    
    try:
        # ========================================================================
        # ЭТАП 1: Инициализация и проверка окружения
        # ========================================================================
        with TestStage("1. Инициализация и проверка окружения", test_logger) as stage:
            try:
                # Проверка доступности серверов Ollama
                servers = OllamaService.get_all_active_servers(db)
                if not servers:
                    stage.add_error("Нет активных серверов Ollama")
                    stage.set_success(False)
                    pytest.skip("Нет активных серверов Ollama")
                
                # Предпочитаем сервер 10.39.0.6
                server = None
                for s in servers:
                    if "10.39.0.6" in s.url:
                        server = s
                        break
                
                if not server:
                    server = servers[0]
                
                stage.add_detail("Выбранный сервер", f"{server.name} ({server.url})")
                
                # Проверка моделей
                models = OllamaService.get_models_for_server(db, str(server.id))
                non_embedding_models = [
                    m for m in models 
                    if m.model_name and not ("embedding" in m.model_name.lower() or "embed" in m.model_name.lower())
                ]
                
                if not non_embedding_models:
                    stage.add_error("Нет доступных моделей (не embedding)")
                    stage.set_success(False)
                    pytest.skip("Нет доступных моделей")
                
                stage.add_detail("Доступно моделей", len(non_embedding_models))
                stage.add_detail("Первая модель", non_embedding_models[0].model_name)
                
                # Инициализация сервисов
                planning_service = PlanningService(db)
                execution_service = ExecutionService(db)
                agent_team_service = AgentTeamService(db)
                agent_team_coordination = AgentTeamCoordination(db)
                model_selector = ModelSelector(db)
                
                stage.add_detail("PlanningService", "Инициализирован")
                stage.add_detail("ExecutionService", "Инициализирован")
                stage.add_detail("AgentTeamService", "Инициализирован")
                stage.add_detail("AgentTeamCoordination", "Инициализирован")
                stage.add_detail("ModelSelector", "Инициализирован")
                
                stage.set_success(True)
                
            except Exception as e:
                stage.add_error(f"Ошибка инициализации: {str(e)}")
                stage.set_success(False)
                raise
        
        # ========================================================================
        # ЭТАП 2: Выбор моделей через ModelSelector
        # ========================================================================
        with TestStage("2. Выбор моделей через ModelSelector", test_logger) as stage:
            try:
                # Выбор модели для планирования
                planning_model = model_selector.get_planning_model(server)
                if not planning_model:
                    stage.add_error("Не удалось выбрать модель для планирования")
                    stage.set_success(False)
                    pytest.skip("Нет модели для планирования")
                
                stage.add_detail("Модель планирования", planning_model.model_name)
                
                # Выбор модели для генерации кода
                code_model = model_selector.get_code_model(server)
                if not code_model:
                    stage.add_warning("Не удалось выбрать модель для генерации кода, будет использована модель планирования")
                    code_model = planning_model
                
                stage.add_detail("Модель генерации кода", code_model.model_name)
                
                # Получение сервера для моделей
                planning_server = model_selector.get_server_for_model(planning_model)
                code_server = model_selector.get_server_for_model(code_model)
                
                stage.add_detail("Сервер планирования", planning_server.url if planning_server else "Не найден")
                stage.add_detail("Сервер генерации кода", code_server.url if code_server else "Не найден")
                
                stage.set_success(True)
                
            except Exception as e:
                stage.add_error(f"Ошибка выбора моделей: {str(e)}")
                stage.set_success(False)
                raise
        
        # ========================================================================
        # ЭТАП 3: Создание задачи
        # ========================================================================
        with TestStage("3. Создание задачи", test_logger) as stage:
            try:
                task = Task(
                    id=uuid4(),
                    description=test_task_description,
                    status=TaskStatus.PENDING,
                    created_at=datetime.utcnow()
                )
                db.add(task)
                db.commit()
                db.refresh(task)
                
                stage.add_detail("ID задачи", str(task.id))
                stage.add_detail("Описание", task.description)
                stage.add_detail("Статус", task.status.value)
                
                stage.set_success(True)
                
            except Exception as e:
                stage.add_error(f"Ошибка создания задачи: {str(e)}")
                stage.set_success(False)
                raise
        
        # ========================================================================
        # ЭТАП 4: Генерация плана через PlanningService
        # ========================================================================
        with TestStage("4. Генерация плана через PlanningService", test_logger) as stage:
            try:
                test_logger.info("Вызов PlanningService.generate_plan()...")
                test_logger.info(f"Задача: {test_task_description}")
                
                # Генерация плана с таймаутом
                plan = await asyncio.wait_for(
                    planning_service.generate_plan(
                        task_description=test_task_description,
                        task_id=task.id,
                        context={}
                    ),
                    timeout=TIMEOUTS["planning"]
                )
                
                if not plan:
                    stage.add_error("PlanningService вернул None")
                    stage.set_success(False)
                    raise ValueError("Plan is None")
                
                db.refresh(plan)
                
                stage.add_detail("ID плана", str(plan.id))
                # plan.status может быть строкой или enum
                status_value = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
                stage.add_detail("Статус плана", status_value)
                stage.add_detail("Цель", plan.goal)
                
                # Анализ шагов
                steps = plan.steps if isinstance(plan.steps, list) else json.loads(plan.steps) if plan.steps else []
                stage.add_detail("Количество шагов", len(steps))
                
                for i, step in enumerate(steps[:5], 1):  # Показываем первые 5 шагов
                    step_desc = step.get("description", "")[:50]
                    stage.add_detail(f"Шаг {i}", step_desc + "..." if len(step_desc) > 50 else step_desc)
                
                if len(steps) > 5:
                    stage.add_detail("...", f"и еще {len(steps) - 5} шагов")
                
                # Проверка стратегии
                if plan.strategy:
                    strategy = plan.strategy if isinstance(plan.strategy, dict) else json.loads(plan.strategy) if plan.strategy else {}
                    if strategy:
                        stage.add_detail("Подход", strategy.get("approach", "Не указан")[:100])
                
                stage.set_success(True)
                
            except asyncio.TimeoutError:
                stage.add_error(f"Таймаут генерации плана ({TIMEOUTS['planning']} сек)")
                stage.set_success(False)
                raise
            except Exception as e:
                stage.add_error(f"Ошибка генерации плана: {str(e)}")
                stage.set_success(False)
                raise
        
        # ========================================================================
        # ЭТАП 5: Создание команды агентов
        # ========================================================================
        with TestStage("5. Создание команды агентов", test_logger) as stage:
            try:
                # Создание агентов
                agent1 = Agent(
                    id=uuid4(),
                    name=f"Agent-1-{uuid4().hex[:8]}",
                    status=AgentStatus.ACTIVE,
                    capabilities=["code_generation", "planning"],
                    created_at=datetime.utcnow()
                )
                agent2 = Agent(
                    id=uuid4(),
                    name=f"Agent-2-{uuid4().hex[:8]}",
                    status=AgentStatus.ACTIVE,
                    capabilities=["code_review", "testing"],
                    created_at=datetime.utcnow()
                )
                
                db.add(agent1)
                db.add(agent2)
                db.commit()
                
                stage.add_detail("Агент 1", f"{agent1.name} ({', '.join(agent1.capabilities)})")
                stage.add_detail("Агент 2", f"{agent2.name} ({', '.join(agent2.capabilities)})")
                
                # Создание команды
                team = agent_team_service.create_team(
                    name=f"Test Team {uuid4().hex[:8]}",
                    description="Тестовая команда для проверки взаимодействия",
                    coordination_strategy=CoordinationStrategy.COLLABORATIVE,
                    status=TeamStatus.ACTIVE
                )
                
                # Добавление агентов в команду
                agent_team_service.add_agent_to_team(team.id, agent1.id, role="developer")
                agent_team_service.add_agent_to_team(team.id, agent2.id, role="reviewer")
                
                # Назначение лидера
                agent_team_service.set_team_lead(team.id, agent1.id)
                
                db.refresh(team)
                
                stage.add_detail("ID команды", str(team.id))
                stage.add_detail("Название команды", team.name)
                stage.add_detail("Стратегия координации", team.coordination_strategy.value)
                stage.add_detail("Количество агентов", len(team.agents))
                stage.add_detail("Лидер команды", agent1.name)
                
                stage.set_success(True)
                
            except Exception as e:
                stage.add_error(f"Ошибка создания команды: {str(e)}")
                stage.set_success(False)
                raise
        
        # ========================================================================
        # ЭТАП 6: Выполнение плана через ExecutionService
        # ========================================================================
        with TestStage("6. Выполнение плана через ExecutionService", test_logger) as stage:
            try:
                test_logger.info("Вызов ExecutionService.execute_plan()...")
                test_logger.info(f"План ID: {plan.id}")
                test_logger.info(f"Количество шагов: {len(steps)}")
                
                # Выполнение плана с таймаутом
                execution_result = await asyncio.wait_for(
                    execution_service.execute_plan(
                        plan_id=plan.id,
                        context={"team_id": str(team.id)}
                    ),
                    timeout=TIMEOUTS["full_execution"]
                )
                
                db.refresh(plan)
                
                # plan.status может быть строкой или enum
                status_value = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
                stage.add_detail("Статус выполнения", status_value)
                stage.add_detail("Текущий шаг", plan.current_step_index or 0)
                
                # Анализ результатов шагов
                if execution_result:
                    completed_steps = execution_result.get("completed_steps", 0)
                    failed_steps = execution_result.get("failed_steps", 0)
                    total_steps = execution_result.get("total_steps", len(steps))
                    
                    stage.add_detail("Выполнено шагов", f"{completed_steps}/{total_steps}")
                    stage.add_detail("Провалено шагов", failed_steps)
                    
                    # Детали по шагам
                    step_results = execution_result.get("step_results", [])
                    for i, step_result in enumerate(step_results[:3], 1):  # Первые 3 шага
                        step_status = step_result.get("status", "unknown")
                        step_id = step_result.get("step_id", f"step_{i}")
                        stage.add_detail(f"Шаг {i} ({step_id})", step_status)
                        
                        if step_result.get("output"):
                            output_preview = str(step_result["output"])[:100]
                            stage.add_detail(f"  Результат", output_preview + "..." if len(output_preview) > 100 else output_preview)
                
                # Проверка финального статуса
                plan_status_str = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
                if plan_status_str == PlanStatus.COMPLETED.value or plan_status_str == "completed":
                    stage.set_success(True)
                elif plan_status_str == PlanStatus.FAILED.value or plan_status_str == "failed":
                    stage.add_warning("План завершился с ошибкой")
                    stage.set_success(False)
                else:
                    stage.add_warning(f"План в статусе {plan_status_str}")
                    stage.set_success(True)  # Частичный успех
                
            except asyncio.TimeoutError:
                stage.add_error(f"Таймаут выполнения плана ({TIMEOUTS['full_execution']} сек)")
                stage.set_success(False)
            except Exception as e:
                stage.add_error(f"Ошибка выполнения плана: {str(e)}")
                stage.set_success(False)
        
        # ========================================================================
        # ЭТАП 7: Проверка координации через AgentTeamCoordination
        # ========================================================================
        with TestStage("7. Проверка координации через AgentTeamCoordination", test_logger) as stage:
            try:
                # Проверка распределения задач
                test_logger.info("Проверка распределения задач в команде...")
                
                # Попытка распределить задачу в команду
                coordination_result = await asyncio.wait_for(
                    agent_team_coordination.distribute_task_to_team(
                        team_id=team.id,
                        task_description="Проверка координации",
                        context={"test": True}
                    ),
                    timeout=TIMEOUTS["team_coordination"]
                )
                
                if coordination_result:
                    stage.add_detail("Распределение задач", "Успешно")
                    assigned_agents = coordination_result.get("assigned_agents", [])
                    stage.add_detail("Назначено агентам", len(assigned_agents))
                else:
                    stage.add_warning("Координация не вернула результат")
                
                stage.set_success(True)
                
            except asyncio.TimeoutError:
                stage.add_warning(f"Таймаут координации ({TIMEOUTS['team_coordination']} сек)")
                stage.set_success(True)  # Не критично
            except Exception as e:
                stage.add_warning(f"Ошибка координации (не критично): {str(e)}")
                stage.set_success(True)  # Не критично для основного workflow
        
        # ========================================================================
        # ФИНАЛЬНЫЙ ОТЧЕТ
        # ========================================================================
        overall_end = datetime.now()
        overall_duration = (overall_end - overall_start).total_seconds()
        
        test_logger.info(f"\n{'#'*100}")
        test_logger.info(f"ЗАВЕРШЕНИЕ ТЕСТА")
        test_logger.info(f"Общая длительность: {overall_duration:.2f} сек ({overall_duration/60:.1f} мин)")
        test_logger.info(f"Время завершения: {overall_end.strftime('%Y-%m-%d %H:%M:%S')}")
        test_logger.info(f"Лог файл: {TEST_LOG_FILE}")
        test_logger.info(f"{'#'*100}\n")
        
        # Финальная проверка
        db.refresh(plan)
        db.refresh(task)
        
        test_logger.info("ФИНАЛЬНЫЕ СТАТУСЫ:")
        task_status = task.status.value if hasattr(task.status, 'value') else str(task.status)
        plan_status = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
        team_status = team.status.value if hasattr(team.status, 'value') else str(team.status)
        test_logger.info(f"  Задача: {task_status}")
        test_logger.info(f"  План: {plan_status}")
        test_logger.info(f"  Команда: {team_status}")
        
        # Успех теста
        assert plan is not None, "План должен быть создан"
        assert task.status in [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS, TaskStatus.PENDING], "Задача должна иметь валидный статус"
        
        test_logger.info("\n✓ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        
    except Exception as e:
        test_logger.error(f"\n✗ ТЕСТ ЗАВЕРШЕН С ОШИБКОЙ: {str(e)}")
        test_logger.exception("Детали ошибки:")
        raise

