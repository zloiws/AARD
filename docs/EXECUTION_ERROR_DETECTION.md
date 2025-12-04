# Механизм обнаружения ошибок выполнения

## Обзор

Механизм обнаружения ошибок выполнения классифицирует ошибки по степени критичности и определяет, требуется ли автоматическое перепланирование. Система использует паттерны и контекст для точной классификации ошибок.

## Архитектура

### Компоненты

1. **ExecutionErrorDetector** (`backend/app/core/execution_error_types.py`)
   - Классификация ошибок по степени критичности
   - Определение необходимости перепланирования
   - Анализ паттернов ошибок

2. **ExecutionError** (`backend/app/core/execution_error_types.py`)
   - Представление ошибки с классификацией
   - Метаданные и контекст ошибки
   - Информация о необходимости перепланирования

3. **Интеграция в ExecutionService** (`backend/app/services/execution_service.py`)
   - Использование классификации при обработке ошибок
   - Автоматическое перепланирование для критических ошибок
   - Логирование классифицированных ошибок

## Классификация ошибок

### Уровни критичности

- **CRITICAL** - Требует немедленного перепланирования
- **HIGH** - Может потребовать перепланирования
- **MEDIUM** - Может быть исправлена без перепланирования
- **LOW** - Не критична, можно продолжить

### Категории ошибок

- **ENVIRONMENT** - Проблемы окружения/инфраструктуры
- **DEPENDENCY** - Отсутствующие зависимости или ресурсы
- **VALIDATION** - Ошибки валидации/формата
- **LOGIC** - Логические ошибки в плане/шаге
- **TIMEOUT** - Ошибки таймаута
- **RESOURCE** - Ограничения ресурсов
- **UNKNOWN** - Неклассифицированные ошибки

## Критические ошибки (требуют перепланирования)

### Ошибки структуры плана
- "Plan has no steps"
- "Invalid plan structure"
- "Plan validation failed"

### Ошибки зависимостей
- "Dependency not found"
- "Missing required dependency"
- "Circular dependency"

### Ошибки окружения
- "No suitable model found"
- "No server found"
- "Database connection failed"

### Ошибки логики
- "Invalid step sequence"
- "Contradictory steps"

## Высокая критичность (могут потребовать перепланирования)

### Ошибки агентов/инструментов
- "Agent not found"
- "Tool not found"
- "Agent not active"
- "Tool not active"

### Ошибки валидации
- "Function call validation failed"
- "Invalid parameters"
- "Missing required parameter"

### Ошибки ресурсов
- "Memory limit exceeded"
- "Resource unavailable"

### Ошибки таймаута
- "Step execution timeout" (становится CRITICAL после нескольких попыток)

## Использование

### Базовое использование

```python
from app.core.execution_error_types import detect_execution_error, requires_replanning

# Классификация ошибки
error = detect_execution_error("Plan has no steps")
print(error.severity)  # ErrorSeverity.CRITICAL
print(error.category)  # ErrorCategory.LOGIC
print(error.requires_replanning)  # True

# Быстрая проверка
if requires_replanning("Dependency not found"):
    # Требуется перепланирование
    pass
```

### С контекстом

```python
context = {
    "step_id": "step_1",
    "step_index": 0,
    "plan_id": "plan-123",
    "retry_count": 2
}

error = detect_execution_error(
    "Step execution timeout",
    context=context
)
```

### В ExecutionService

```python
execution_service = ExecutionService(db)

# Проверка критичности
is_critical = execution_service._is_critical_error(
    error_message="Plan has no steps",
    context={"plan_id": str(plan.id)}
)

# Классификация
classified_error = execution_service._classify_error(
    error_message=error_message,
    context=context
)

if classified_error.requires_replanning:
    await execution_service._handle_plan_failure(
        plan,
        error_message,
        execution_context,
        classified_error=classified_error
    )
```

## Интеграция с автоматическим перепланированием

Механизм обнаружения ошибок автоматически интегрирован с `ExecutionService`:

1. При ошибке выполнения шага ошибка классифицируется
2. Для CRITICAL и HIGH ошибок автоматически запускается перепланирование
3. Для MEDIUM и LOW ошибок перепланирование не запускается

### Пример потока

```
1. Ошибка при выполнении шага
   ↓
2. Классификация ошибки (ExecutionErrorDetector)
   ↓
3. Проверка requires_replanning
   ↓
4. Если True → _handle_plan_failure() → replan()
   ↓
5. Если False → логирование, продолжение/откат
```

## Расширение

Для добавления новых паттернов ошибок:

1. Добавьте паттерн в соответствующий список в `ExecutionErrorDetector`:
   - `CRITICAL_PATTERNS` - для критических ошибок
   - `HIGH_PATTERNS` - для ошибок высокой критичности
   - `TIMEOUT_PATTERNS` - для ошибок таймаута

2. Пример:
```python
CRITICAL_PATTERNS = [
    # ... существующие паттерны
    (r"new.*critical.*pattern", ErrorCategory.CATEGORY, ErrorSeverity.CRITICAL),
]
```

## Тестирование

- Частные тесты: `backend/tests/test_execution_error_detection.py`
- Интеграционные тесты: `backend/tests/integration/test_auto_replan_trigger.py`

Запуск тестов:
```bash
pytest backend/tests/test_execution_error_detection.py -v
pytest backend/tests/integration/test_auto_replan_trigger.py -v
```

## Связанные компоненты

- `ExecutionService` - использует классификацию ошибок
- `PlanningService.replan()` - вызывается для критических ошибок
- `ReflectionService` - анализирует ошибки перед перепланированием

