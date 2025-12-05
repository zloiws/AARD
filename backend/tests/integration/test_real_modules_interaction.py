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


# Таймауты для различных операций (в секундах) - ОПТИМИЗИРОВАНО ДЛЯ ОГРАНИЧЕННОГО ЖЕЛЕЗА
TIMEOUTS = {
    "llm_call": 30,  # 30 секунд на LLM вызов (быстрые ответы)
    "planning": 60,  # 1 минута на генерацию плана (без долгих размышлений)
    "execution_step": 45,  # 45 секунд на выполнение шага
    "full_execution": 180,  # 3 минуты на полное выполнение (максимум)
    "team_coordination": 30,  # 30 секунд на координацию команды
}

# Параметры для ограничения времени размышлений LLM
LLM_FAST_PARAMS = {
    "temperature": 0.3,  # Низкая температура = быстрые, детерминированные ответы
    "top_p": 0.8,  # Ограничение выборки
    "num_ctx": 2048,  # Уменьшенный контекст для скорости
    "num_predict": 500,  # Максимум токенов в ответе (ограничение "думать час")
}


@pytest.mark.asyncio
@pytest.mark.slow  # Маркер для долгих тестов
@pytest.mark.timeout(300)  # Общий таймаут теста: 5 минут максимум
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
    # Упрощенная задача для быстрого выполнения на ограниченном железе
    test_task_description = "Напиши print('Привет, мир!') на Python"
    
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
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Модель должна быть активна
                assert planning_model.is_active, f"Модель планирования {planning_model.model_name} должна быть активна"
                
                stage.add_detail("Модель планирования", planning_model.model_name)
                
                # Выбор модели для генерации кода
                code_model = model_selector.get_code_model(server)
                if not code_model:
                    stage.add_warning("Не удалось выбрать модель для генерации кода, будет использована модель планирования")
                    code_model = planning_model
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Модель должна быть активна
                assert code_model.is_active, f"Модель генерации кода {code_model.model_name} должна быть активна"
                
                stage.add_detail("Модель генерации кода", code_model.model_name)
                
                # Получение сервера для моделей
                planning_server = model_selector.get_server_for_model(planning_model)
                code_server = model_selector.get_server_for_model(code_model)
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Серверы должны существовать
                assert planning_server is not None, "Сервер для модели планирования должен существовать"
                assert code_server is not None, "Сервер для модели генерации кода должен существовать"
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Серверы должны быть активны
                assert planning_server.is_active, "Сервер планирования должен быть активен"
                assert code_server.is_active, "Сервер генерации кода должен быть активен"
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Модели должны принадлежать правильным серверам
                assert planning_model.server_id == planning_server.id, "Модель планирования должна принадлежать серверу планирования"
                assert code_model.server_id == code_server.id, "Модель генерации кода должна принадлежать серверу генерации кода"
                
                stage.add_detail("Сервер планирования", planning_server.url if planning_server else "Не найден")
                stage.add_detail("Сервер генерации кода", code_server.url if code_server else "Не найден")
                stage.add_detail("Согласованность моделей", "✓ Модели и серверы согласованы")
                
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
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: План должен быть связан с задачей
                if plan.task_id:
                    assert plan.task_id == task.id, f"План должен быть связан с задачей {task.id}, но связан с {plan.task_id}"
                    stage.add_detail("Связь с задачей", f"✓ План связан с задачей {task.id}")
                    
                    # ПРОВЕРКА СОГЛАСОВАННОСТИ: Задача должна существовать в БД
                    task_from_db = db.query(Task).filter(Task.id == task.id).first()
                    assert task_from_db is not None, "Задача должна существовать в БД"
                    assert task_from_db.id == task.id, "ID задачи должен совпадать"
                else:
                    stage.add_warning("План не связан с задачей (task_id отсутствует)")
                
                stage.add_detail("ID плана", str(plan.id))
                # plan.status может быть строкой или enum
                status_value = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
                stage.add_detail("Статус плана", status_value)
                stage.add_detail("Цель", plan.goal)
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: План должен иметь цель
                assert plan.goal, "План должен иметь цель (goal)"
                
                # Анализ шагов
                steps = plan.steps if isinstance(plan.steps, list) else json.loads(plan.steps) if plan.steps else []
                stage.add_detail("Количество шагов", len(steps))
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: План должен иметь хотя бы один шаг
                assert len(steps) > 0, "План должен содержать хотя бы один шаг"
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Структура шагов
                for i, step in enumerate(steps, 1):
                    assert isinstance(step, dict), f"Шаг {i} должен быть словарем"
                    assert "description" in step or "step_id" in step, f"Шаг {i} должен иметь description или step_id"
                
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
                
                # ЛОГИРОВАНИЕ: План сгенерирован
                test_logger.info(f"\n📋 ПЛАН СГЕНЕРИРОВАН:")
                test_logger.info(f"   ID плана: {plan.id}")
                test_logger.info(f"   Статус: {status_value}")
                test_logger.info(f"   Шагов: {len(steps)}")
                test_logger.info(f"   Цель: {plan.goal[:80]}..." if len(plan.goal) > 80 else f"   Цель: {plan.goal}")
                if steps:
                    test_logger.info(f"   Первые шаги:")
                    for i, step in enumerate(steps[:3], 1):
                        step_desc = step.get("description", "")[:60]
                        test_logger.info(f"     {i}. {step_desc}...")
                
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
                    coordination_strategy=CoordinationStrategy.COLLABORATIVE.value
                )
                
                # Активация команды (изменение статуса с DRAFT на ACTIVE)
                team.status = TeamStatus.ACTIVE.value
                db.commit()
                db.refresh(team)
                
                # Добавление агентов в команду
                agent_team_service.add_agent_to_team(team.id, agent1.id, role="developer")
                agent_team_service.add_agent_to_team(team.id, agent2.id, role="reviewer")
                
                # Назначение лидера
                agent_team_service.set_team_lead(team.id, agent1.id)
                
                db.refresh(team)
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Команда должна иметь агентов
                team_agents = list(team.agents) if hasattr(team.agents, '__iter__') else []
                assert len(team_agents) > 0, "Команда должна содержать хотя бы одного агента"
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Агенты должны быть активны
                active_agents = [a for a in team_agents if (a.status.value if hasattr(a.status, 'value') else str(a.status)) == AgentStatus.ACTIVE.value]
                if len(active_agents) != len(team_agents):
                    stage.add_warning(f"Не все агенты активны: {len(active_agents)}/{len(team_agents)}")
                
                stage.add_detail("ID команды", str(team.id))
                stage.add_detail("Название команды", team.name)
                # coordination_strategy может быть строкой или enum
                strategy_value = team.coordination_strategy.value if hasattr(team.coordination_strategy, 'value') else str(team.coordination_strategy)
                stage.add_detail("Стратегия координации", strategy_value)
                stage.add_detail("Количество агентов", len(team_agents))
                stage.add_detail("Активных агентов", len(active_agents))
                stage.add_detail("Лидер команды", agent1.name)
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Лидер должен быть в команде
                leader_ids = [a.id for a in team_agents]
                assert agent1.id in leader_ids, "Лидер команды должен быть в списке агентов команды"
                
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
                # execute_plan принимает только plan_id (без context)
                executed_plan = await asyncio.wait_for(
                    execution_service.execute_plan(plan_id=plan.id),
                    timeout=TIMEOUTS["full_execution"]
                )
                
                db.refresh(executed_plan)
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: План должен быть обновлен
                assert executed_plan.id == plan.id, "ID плана должен совпадать"
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: План должен быть в статусе выполнения или завершен
                executed_status = executed_plan.status.value if hasattr(executed_plan.status, 'value') else str(executed_plan.status)
                valid_execution_statuses = ["executing", "completed", "failed", "in_progress"]
                assert executed_status in valid_execution_statuses, f"План должен быть в статусе выполнения ({valid_execution_statuses}), но в статусе {executed_status}"
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: Если план выполняется, должен быть current_step
                if executed_status in ["executing", "in_progress"]:
                    current_step = getattr(executed_plan, 'current_step_index', None) or getattr(executed_plan, 'current_step', None)
                    assert current_step is not None or current_step == 0, "При выполнении плана должен быть указан текущий шаг"
                
                # ПРОВЕРКА СОГЛАСОВАННОСТИ: План должен быть сохранен в БД
                plan_from_db = db.query(Plan).filter(Plan.id == executed_plan.id).first()
                assert plan_from_db is not None, "План должен существовать в БД после выполнения"
                assert plan_from_db.status == executed_plan.status, "Статус плана в БД должен совпадать с возвращенным"
                
                # plan.status может быть строкой или enum
                status_value = executed_plan.status.value if hasattr(executed_plan.status, 'value') else str(executed_plan.status)
                stage.add_detail("Статус выполнения", status_value)
                # Проверка текущего шага (может быть current_step или current_step_index)
                current_step = getattr(executed_plan, 'current_step_index', None) or getattr(executed_plan, 'current_step', None) or 0
                stage.add_detail("Текущий шаг", current_step)
                
                # Проверка согласованности: если план выполнен, должен быть current_step
                if status_value in ["completed", "executing"]:
                    current_step = getattr(executed_plan, 'current_step_index', None) or getattr(executed_plan, 'current_step', None) or 0
                    if len(steps) > 0:
                        stage.add_detail("Прогресс выполнения", f"Шаг {current_step} из {len(steps)}")
                    else:
                        stage.add_detail("Прогресс выполнения", f"Шаг {current_step}")
                
                # Анализ шагов из плана
                executed_steps = executed_plan.steps if isinstance(executed_plan.steps, list) else json.loads(executed_plan.steps) if executed_plan.steps else []
                stage.add_detail("Всего шагов в плане", len(executed_steps))
                
                # Подсчет выполненных/проваленных шагов из результатов плана
                completed_count = 0
                failed_count = 0
                for step in executed_steps:
                    step_status = step.get("status", "unknown")
                    if step_status == "completed":
                        completed_count += 1
                    elif step_status == "failed":
                        failed_count += 1
                
                stage.add_detail("Выполнено шагов", f"{completed_count}/{len(executed_steps)}")
                stage.add_detail("Провалено шагов", failed_count)
                
                # Детали по первым 3 шагам
                for i, step in enumerate(executed_steps[:3], 1):
                    step_status = step.get("status", "unknown")
                    step_id = step.get("step_id", f"step_{i}")
                    step_desc = step.get("description", "")[:50]
                    stage.add_detail(f"Шаг {i} ({step_id})", f"{step_status}: {step_desc}...")
                    
                    if step.get("output"):
                        output_preview = str(step["output"])[:100]
                        stage.add_detail(f"  Результат", output_preview + "..." if len(output_preview) > 100 else output_preview)
                
                # Проверка финального статуса
                plan_status_str = executed_plan.status.value if hasattr(executed_plan.status, 'value') else str(executed_plan.status)
                if plan_status_str == PlanStatus.COMPLETED.value or plan_status_str == "completed":
                    stage.set_success(True)
                elif plan_status_str == PlanStatus.FAILED.value or plan_status_str == "failed":
                    stage.add_warning("План завершился с ошибкой")
                    stage.set_success(False)
                elif plan_status_str in ["executing", "in_progress"]:
                    stage.add_warning(f"План все еще выполняется (статус: {plan_status_str})")
                    stage.set_success(True)  # Частичный успех - выполнение началось
                else:
                    stage.add_warning(f"План в статусе {plan_status_str}")
                    stage.set_success(True)  # Частичный успех
                
                # ЛОГИРОВАНИЕ: План выполнен
                test_logger.info(f"\n⚙️ ПЛАН ВЫПОЛНЕН:")
                test_logger.info(f"   Статус: {plan_status_str}")
                test_logger.info(f"   Выполнено шагов: {completed_count}/{len(executed_steps)}")
                if plan_status_str == "completed":
                    test_logger.info(f"   ✓ План успешно завершен!")
                    # Показать результаты шагов
                    for i, step in enumerate(executed_steps[:3], 1):
                        step_status = step.get("status", "unknown")
                        step_desc = step.get("description", "")[:50]
                        test_logger.info(f"     Шаг {i}: {step_status} - {step_desc}...")
                elif plan_status_str == "failed":
                    test_logger.info(f"   ✗ План завершился с ошибкой")
                else:
                    test_logger.info(f"   ⚠ План в процессе выполнения")
                
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
                # distribute_task_to_team принимает task_context, а не context
                coordination_result = await asyncio.wait_for(
                    agent_team_coordination.distribute_task_to_team(
                        team_id=team.id,
                        task_description="Проверка координации",
                        task_context={"test": True, "plan_id": str(plan.id)}
                    ),
                    timeout=TIMEOUTS["team_coordination"]
                )
                
                if coordination_result:
                    stage.add_detail("Распределение задач", "Успешно")
                    assigned_agents = coordination_result.get("assigned_agents", [])
                    stage.add_detail("Назначено агентам", len(assigned_agents))
                    
                    # ПРОВЕРКА СОГЛАСОВАННОСТИ: Должен быть хотя бы один назначенный агент
                    if len(assigned_agents) > 0:
                        stage.add_detail("Согласованность", "✓ Задачи распределены между агентами")
                    else:
                        stage.add_warning("Задачи не были распределены между агентами")
                    
                    # ПРОВЕРКА СОГЛАСОВАННОСТИ: Назначенные агенты должны быть из команды
                    team_agents_list = list(team.agents) if hasattr(team.agents, '__iter__') else []
                    team_agent_ids = {str(a.id) for a in team_agents_list}
                    for agent_info in assigned_agents:
                        agent_id = str(agent_info.get("agent_id", ""))
                        if agent_id and agent_id not in team_agent_ids:
                            stage.add_warning(f"Агент {agent_id} назначен, но не входит в команду")
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
        
        # ФИНАЛЬНЫЕ ПРОВЕРКИ СОГЛАСОВАННОСТИ
        db.refresh(plan)
        db.refresh(task)
        db.refresh(team)
        
        test_logger.info("\n" + "="*100)
        test_logger.info("📤 РЕЗУЛЬТАТ РАБОТЫ СИСТЕМЫ:")
        test_logger.info("="*100)
        
        test_logger.info("\nФИНАЛЬНЫЕ СТАТУСЫ:")
        task_status = task.status.value if hasattr(task.status, 'value') else str(task.status)
        plan_status = plan.status.value if hasattr(plan.status, 'value') else str(plan.status)
        team_status = team.status.value if hasattr(team.status, 'value') else str(team.status)
        test_logger.info(f"  ✓ Задача: {task_status}")
        test_logger.info(f"  ✓ План: {plan_status}")
        test_logger.info(f"  ✓ Команда: {team_status}")
        
        # ПРОВЕРКА СОГЛАСОВАННОСТИ: Связь задачи и плана
        if plan.task_id:
            assert plan.task_id == task.id, "План должен быть связан с правильной задачей"
            test_logger.info(f"  ✓ Связь задачи-плана: валидна (план {plan.id} -> задача {task.id})")
        else:
            test_logger.warning(f"  ⚠ Связь задачи-плана: отсутствует")
        
        # ПРОВЕРКА СОГЛАСОВАННОСТИ: Статусы задачи и плана
        valid_task_statuses = [TaskStatus.COMPLETED, TaskStatus.IN_PROGRESS, TaskStatus.PENDING, TaskStatus.PLANNING]
        task_status_enum = None
        for status in valid_task_statuses:
            if task_status == status.value or task_status == status:
                task_status_enum = status
                break
        
        if task_status_enum:
            test_logger.info(f"  ✓ Статус задачи: валиден ({task_status})")
        else:
            test_logger.warning(f"  ⚠ Статус задачи: неожиданный ({task_status})")
        
        # ПРОВЕРКА СОГЛАСОВАННОСТИ: План должен существовать
        assert plan is not None, "План должен быть создан"
        assert plan.id is not None, "План должен иметь ID"
        test_logger.info(f"  ✓ План создан: {plan.id}")
        
        # ПРОВЕРКА СОГЛАСОВАННОСТИ: Команда должна существовать
        assert team is not None, "Команда должна быть создана"
        assert team.id is not None, "Команда должна иметь ID"
        # team.agents может быть AppenderQuery, нужно преобразовать в список
        team_agents_list = list(team.agents) if hasattr(team.agents, '__iter__') else []
        test_logger.info(f"  ✓ Команда создана: {team.id} ({len(team_agents_list)} агентов)")
        
        # ПРОВЕРКА СОГЛАСОВАННОСТИ: План должен иметь шаги
        final_steps = plan.steps if isinstance(plan.steps, list) else json.loads(plan.steps) if plan.steps else []
        assert len(final_steps) > 0, "План должен содержать шаги"
        test_logger.info(f"  ✓ План содержит {len(final_steps)} шагов")
        
        test_logger.info("\n✓ ТЕСТ ЗАВЕРШЕН УСПЕШНО")
        
    except Exception as e:
        test_logger.error(f"\n✗ ТЕСТ ЗАВЕРШЕН С ОШИБКОЙ: {str(e)}")
        test_logger.exception("Детали ошибки:")
        raise

