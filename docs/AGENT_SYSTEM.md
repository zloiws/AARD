# Agent System

## Обзор

Agent System обеспечивает автоматический выбор и использование агентов для выполнения задач планирования и выполнения. Агенты выбираются на основе их capabilities и метрик производительности.

## Архитектура

### Компоненты

1. **AgentService** (`backend/app/services/agent_service.py`)
   - Управление жизненным циклом агентов
   - Выбор подходящего агента для задачи
   - Метрики производительности

2. **Agent Model** (`backend/app/models/agent.py`)
   - Модель данных агента
   - Capabilities (JSONB)
   - Метрики (success_rate, average_execution_time)

3. **PlanningService Integration** (`backend/app/services/planning_service.py`)
   - Автоматический выбор агента для задачи
   - Назначение агента шагам плана

4. **ExecutionService Integration** (`backend/app/services/execution_service.py`)
   - Выполнение шагов через агентов
   - Интеграция с SimpleAgent

## Выбор агента для задачи

### Автоматический выбор

PlanningService автоматически выбирает подходящего агента на основе:

1. **Требуемых capabilities** - определяется по анализу описания задачи
2. **Метрик производительности** - success_rate, average_execution_time
3. **Предпочтений** - можно указать preferred_agent_id в контексте

### Определение capabilities

Система использует простые эвристики для определения требуемых capabilities:

```python
# По умолчанию: planning
required_capabilities = [AgentCapability.PLANNING.value]

# Добавляется code_generation, если в описании есть ключевые слова
if any(keyword in task_description.lower() for keyword in ["code", "program", "script"]):
    required_capabilities.append(AgentCapability.CODE_GENERATION.value)

# Добавляется code_analysis, если есть ключевые слова анализа
if any(keyword in task_description.lower() for keyword in ["analyze", "review", "test"]):
    required_capabilities.append(AgentCapability.CODE_ANALYSIS.value)
```

### Алгоритм выбора

Агент выбирается на основе взвешенной оценки:

```
Score = (
    capability_score * 0.5 +    # Соответствие capabilities (50%)
    success_score * 0.3 +       # Успешность выполнения (30%)
    time_score * 0.2            # Скорость выполнения (20%)
)
```

Выбирается агент с наивысшим score.

## Использование

### В PlanningService

```python
from app.services.planning_service import PlanningService

planning_service = PlanningService(db)

# Автоматический выбор агента
plan = await planning_service.generate_plan(
    task_description="Create a Python script",
    context={}
)

# С указанным агентом
plan = await planning_service.generate_plan(
    task_description="Create a Python script",
    context={"agent_id": str(agent_id)}
)
```

### Выбор агента напрямую

```python
from app.services.agent_service import AgentService
from app.models.agent import AgentCapability

agent_service = AgentService(db)

selected_agent = agent_service.select_agent_for_task(
    required_capabilities=[
        AgentCapability.PLANNING.value,
        AgentCapability.CODE_GENERATION.value
    ],
    preferred_agent_id=optional_preferred_id
)
```

## Интеграция с выполнением

ExecutionService уже интегрирован с агентами:

```python
# Если шаг указывает agent_id, выполнение делегируется агенту
step = {
    "step_id": "step_1",
    "agent": str(agent_id),
    "description": "Execute task",
    "type": "action"
}
```

## Capabilities агентов

Поддерживаемые capabilities:

- `code_generation` - Генерация кода
- `code_analysis` - Анализ кода
- `planning` - Планирование задач
- `reasoning` - Рассуждения
- `data_processing` - Обработка данных
- `text_generation` - Генерация текста
- `research` - Исследование
- `testing` - Тестирование
- `deployment` - Развертывание
- `monitoring` - Мониторинг

## Метрики агентов

Система отслеживает:

- `total_tasks_executed` - Общее количество выполненных задач
- `successful_tasks` - Успешных задач
- `failed_tasks` - Неудачных задач
- `success_rate` - Процент успешности (в формате "85.50%")
- `average_execution_time` - Среднее время выполнения (в секундах)
- `last_used_at` - Время последнего использования

## Digital Twin Integration

Информация о выбранном агенте сохраняется в Digital Twin context:

```json
{
  "agent_selection": {
    "available_agents": [],
    "selected_agents": [
      {
        "agent_id": "...",
        "agent_name": "...",
        "capabilities": ["planning"],
        "reason": "Auto-selected based on task requirements"
      }
    ],
    "selected_agent_id": "...",
    "reasons": {}
  }
}
```

## Тестирование

### Частные тесты

```bash
pytest backend/tests/test_agent_selection.py -v
```

### Интеграционные тесты

```bash
pytest backend/tests/integration/test_agent_planning.py -v
```

## Связанные компоненты

- **PlanningService** - использует выбор агента
- **ExecutionService** - выполняет шаги через агентов
- **AgentService** - управление агентами
- **SimpleAgent** - реализация агента

## Расширение

### Добавление новых capabilities

1. Добавьте capability в `AgentCapability` enum:

```python
class AgentCapability(str, Enum):
    # ... существующие
    NEW_CAPABILITY = "new_capability"
```

2. Обновите логику определения capabilities в PlanningService

3. Создайте агентов с новой capability

### Улучшение алгоритма выбора

Модифицируйте метод `select_agent_for_task` в `AgentService`:

```python
def score_agent(agent: Agent) -> float:
    # Добавьте новые факторы:
    # - Репутация агента
    # - Загрузка агента
    # - Специализация агента
    # и т.д.
    pass
```

