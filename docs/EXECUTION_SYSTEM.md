# Execution System

## Обзор

Execution System отвечает за выполнение планов пошагово, с поддержкой checkpoint'ов, обработкой ошибок и автоматическим перепланированием при критических сбоях.

## Архитектура

### Основные компоненты

1. **ExecutionService** (`backend/app/services/execution_service.py`)
   - Главный сервис для выполнения планов
   - Управление жизненным циклом выполнения
   - Интеграция с checkpoint'ами и обработкой ошибок

2. **StepExecutor** (`backend/app/services/execution_service.py`)
   - Выполнение отдельных шагов плана
   - Поддержка различных типов шагов (action, decision, validation)
   - Интеграция с агентами и инструментами

3. **CheckpointService** (`backend/app/services/checkpoint_service.py`)
   - Создание checkpoint'ов состояния
   - Восстановление из checkpoint'ов
   - Откат при ошибках

4. **ExecutionErrorDetector** (`backend/app/core/execution_error_types.py`)
   - Классификация ошибок выполнения
   - Определение необходимости перепланирования
   - Анализ критичности ошибок

## Выполнение планов

### Процесс выполнения

```
1. Валидация плана (должен быть approved)
   ↓
2. Для каждого шага:
   a. Создание checkpoint'а
   b. Проверка зависимостей
   c. Выполнение шага
   d. Сохранение результата в контекст
   e. Обработка ошибок (если есть)
   ↓
3. Завершение выполнения (completed/failed)
```

### Выполнение шага

Шаг может быть выполнен несколькими способами:

1. **Через агента** - если шаг указывает `agent_id`
2. **Через инструмент** - если шаг указывает `tool_id`
3. **Через LLM** - прямое выполнение с помощью модели кодирования

### Типы шагов

- **action** - действие, требующее выполнения
- **decision** - решение, требующее анализа
- **validation** - проверка условий

## Checkpoint System

### Автоматические checkpoint'ы

Перед каждым шагом автоматически создается checkpoint:

```python
checkpoint = checkpoint_service.create_plan_checkpoint(
    plan,
    reason=f"Checkpoint before step {i + 1}: {description}"
)
```

### Восстановление при ошибках

При ошибке выполнения система пытается откатиться к последнему checkpoint'у:

```python
latest_checkpoint = checkpoint_service.get_latest_checkpoint("plan", plan.id)
if latest_checkpoint:
    checkpoint_service.rollback_entity("plan", plan.id, latest_checkpoint.id)
```

## Обработка ошибок

### Классификация ошибок

Ошибки классифицируются по:
- **Критичности**: CRITICAL, HIGH, MEDIUM, LOW
- **Категории**: ENVIRONMENT, DEPENDENCY, VALIDATION, LOGIC, TIMEOUT, RESOURCE, UNKNOWN

### Автоматическое перепланирование

Для критических ошибок автоматически запускается перепланирование:

```python
classified_error = execution_service._classify_error(
    error_message=error_message,
    context=error_context
)

if execution_service._should_trigger_replanning(classified_error, plan, context):
    await execution_service._handle_plan_failure(
        plan,
        error_message,
        execution_context,
        classified_error=classified_error
    )
```

Подробнее: [EXECUTION_ERROR_DETECTION.md](./EXECUTION_ERROR_DETECTION.md)

## Зависимости между шагами

Шаги могут зависеть от результатов других шагов:

```json
{
  "step_id": "step_2",
  "dependencies": ["step_1"],
  "description": "Second step"
}
```

Перед выполнением шага проверяются все зависимости:

```python
dependencies = step.get("dependencies", [])
for dep_id in dependencies:
    if dep_id not in execution_context:
        # Ошибка: зависимость не выполнена
        raise ValueError(f"Dependency {dep_id} not found")
```

## Контекст выполнения

Контекст выполнения хранит результаты всех выполненных шагов:

```python
execution_context = {
    "step_1": {
        "status": "completed",
        "output": "...",
        "metadata": {...}
    },
    "step_2": {
        "status": "completed",
        "output": "..."
    }
}
```

Результаты шагов используются для:
- Проверки зависимостей
- Передачи данных между шагами
- Анализа при перепланировании

## Интеграция с агентами

Если шаг указывает агента, выполнение делегируется агенту:

```python
if agent_id:
    agent_result = await agent.execute(
        task_description=step.get("description"),
        context=context,
        tool_name=tool_data.name if tool_id else None,
        tool_params=step_inputs
    )
```

## Интеграция с инструментами

Шаги могут использовать инструменты напрямую:

```python
if tool_id:
    tool_result = await tool.execute(**tool_params)
```

## Утверждение шагов

Некоторые шаги могут требовать утверждения перед выполнением:

```json
{
  "step_id": "step_1",
  "approval_required": true,
  "description": "Critical step"
}
```

В этом случае создается запрос на утверждение, и выполнение приостанавливается.

## Метрики и мониторинг

Система отслеживает:

- Время выполнения плана
- Время выполнения каждого шага
- Статус выполнения
- Количество успешных/неуспешных выполнений

Метрики доступны через Prometheus:

- `plan_executions_total` - общее количество выполнений планов
- `plan_execution_duration_seconds` - длительность выполнения
- `plan_steps_total` - количество шагов
- `plan_step_duration_seconds` - длительность выполнения шага

## Использование

### Базовое выполнение плана

```python
from app.services.execution_service import ExecutionService

execution_service = ExecutionService(db)
executed_plan = await execution_service.execute_plan(plan_id)

print(f"Status: {executed_plan.status}")
print(f"Current step: {executed_plan.current_step}")
```

### Получение статуса выполнения

```python
status = execution_service.get_execution_status(plan_id)

print(f"Progress: {status['progress']}%")
print(f"Current step: {status['current_step']}/{status['total_steps']}")
```

### Обработка ошибок

Ошибки обрабатываются автоматически. При критической ошибке:
1. Создается checkpoint для отката
2. Ошибка классифицируется
3. Запускается автоматическое перепланирование (если включено)

## Конфигурация

Настройки автоматического перепланирования в `.env`:

```env
ENABLE_AUTO_REPLANNING=true
AUTO_REPLANNING_MAX_ATTEMPTS=3
AUTO_REPLANNING_TRIGGER_CRITICAL=true
AUTO_REPLANNING_TRIGGER_HIGH=true
AUTO_REPLANNING_TRIGGER_MEDIUM=false
AUTO_REPLANNING_REQUIRE_HUMAN_INTERVENTION_AFTER=2
```

## Тестирование

### Частные тесты

```bash
pytest backend/tests/test_plan_execution.py -v
```

### Интеграционные тесты

```bash
pytest backend/tests/integration/test_full_plan_execution.py -v
```

### Тесты обработки ошибок

```bash
pytest backend/tests/test_execution_error_detection.py -v
```

## Связанные компоненты

- **PlanningService** - создание и перепланирование планов
- **CheckpointService** - управление checkpoint'ами
- **ReflectionService** - анализ ошибок для перепланирования
- **AgentService** - выполнение шагов через агентов
- **ToolService** - использование инструментов

## Расширение

### Добавление нового типа шага

1. Добавьте обработку в `StepExecutor.execute_step()`:

```python
if step_type == "new_type":
    result = await self._execute_new_type_step(step, plan, context, result)
```

2. Реализуйте метод `_execute_new_type_step()`:

```python
async def _execute_new_type_step(
    self,
    step: Dict[str, Any],
    plan: Plan,
    context: Optional[Dict[str, Any]],
    result: Dict[str, Any]
) -> Dict[str, Any]:
    # Реализация выполнения нового типа шага
    pass
```

### Добавление новой стратегии обработки ошибок

Расширьте `ExecutionErrorDetector` новыми паттернами:

```python
CRITICAL_PATTERNS = [
    # ... существующие паттерны
    (r"new.*error.*pattern", ErrorCategory.CATEGORY, ErrorSeverity.CRITICAL),
]
```

## Будущие улучшения

- [ ] Параллельное выполнение независимых шагов
- [ ] Улучшенная визуализация выполнения
- [ ] Расширенная аналитика выполнения
- [ ] Поддержка условного выполнения шагов
- [ ] Retry механизм для неуспешных шагов

