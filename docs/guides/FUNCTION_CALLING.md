# Function Calling Protocol

## Обзор

Function Calling Protocol обеспечивает безопасный и структурированный интерфейс между моделью планирования (модель "Размышлений") и выполнением кода (модель "Кода"). Это ключевой компонент dual-model архитектуры, который разделяет ответственность между планированием и выполнением.

## Концепция

Вместо того, чтобы модель планирования генерировала код напрямую, она создает структурированные function calls, которые затем валидируются и безопасно выполняются.

### Преимущества

1. **Безопасность:** Код валидируется перед выполнением
2. **Разделение ответственности:** Планирование отделено от выполнения
3. **Контроль:** Можно контролировать, какие функции разрешены
4. **Отслеживаемость:** Все вызовы функций логируются

## Структура Function Call

```json
{
    "function": "code_execution_tool",
    "parameters": {
        "code": "print('Hello, World!')",
        "language": "python"
    },
    "validation_schema": {
        "type": "object",
        "required": ["code", "language"],
        "properties": {
            "code": {"type": "string"},
            "language": {"type": "string"}
        }
    },
    "safety_checks": true
}
```

## Разрешенные функции

Система использует whitelist подход - разрешены только определенные функции:

- `code_execution_tool` - выполнение кода в sandbox
- `file_operations_tool` - операции с файлами
- `database_query_tool` - запросы к базе данных
- `http_request_tool` - HTTP запросы

## Использование

### Создание Function Call

```python
from app.core.function_calling import FunctionCallProtocol

call = FunctionCallProtocol.create_function_call(
    function_name="code_execution_tool",
    parameters={
        "code": "def add(a, b):\n    return a + b",
        "language": "python"
    },
    safety_checks=True
)
```

### Валидация

```python
is_valid, issues = FunctionCallProtocol.validate_function_call(call)

if not is_valid:
    print(f"Validation failed: {issues}")
```

### Парсинг из LLM ответа

```python
llm_response = """{
    "function": "code_execution_tool",
    "parameters": {
        "code": "print('Hello')",
        "language": "python"
    }
}"""

call = FunctionCallProtocol.parse_function_call_from_llm(llm_response)
```

## Безопасность

### Проверки безопасности

1. **Whitelist функций:** Только разрешенные функции могут быть вызваны
2. **Обязательные параметры:** Проверка наличия всех обязательных параметров
3. **Валидация схемы:** Проверка типов и структуры параметров
4. **Обнаружение опасного кода:**
   - `os.system`, `subprocess` - системные вызовы
   - `eval`, `exec`, `__import__` - динамическое выполнение
   - `open`, `file` - доступ к файловой системе
5. **SQL Injection:** Обнаружение опасных SQL запросов

### Примеры опасного кода

```python
# Обнаруживается как опасный:
"import os; os.system('rm -rf /')"
"eval(user_input)"
"exec(malicious_code)"
```

## Интеграция в PlanningService

PlanningService теперь генерирует function calls в шагах плана:

```python
# В шаге плана может быть:
{
    "step_id": "step_1",
    "description": "Выполнить вычисления",
    "function_call": {
        "function": "code_execution_tool",
        "parameters": {
            "code": "result = 2 + 2",
            "language": "python"
        }
    }
}
```

## Интеграция в ExecutionService

ExecutionService обрабатывает function calls:

```python
# Если в шаге есть function_call:
if "function_call" in step:
    call = FunctionCallProtocol.parse_function_call_from_llm(step["function_call"])
    is_valid, issues = FunctionCallProtocol.validate_function_call(call)
    
    if is_valid:
        # Выполнить через CodeExecutionSandbox (будет реализовано)
        result = await sandbox.execute_code_safely(...)
```

## Тестирование

```bash
python -m pytest tests/integration/test_function_calling.py -v
```

## Примеры

### Пример 1: Простое выполнение кода

```python
call = FunctionCallProtocol.create_function_call(
    function_name="code_execution_tool",
    parameters={
        "code": "x = 1 + 1\nprint(x)",
        "language": "python"
    }
)

is_valid, issues = FunctionCallProtocol.validate_function_call(call)
assert is_valid
```

### Пример 2: С валидацией схемы

```python
call = FunctionCallProtocol.create_function_call(
    function_name="code_execution_tool",
    parameters={
        "code": "print('Hello')",
        "language": "python"
    },
    validation_schema={
        "type": "object",
        "required": ["code", "language"],
        "properties": {
            "code": {"type": "string", "minLength": 1},
            "language": {"type": "string", "enum": ["python", "javascript"]}
        }
    }
)
```

### Пример 3: Обнаружение опасного кода

```python
call = FunctionCallProtocol.create_function_call(
    function_name="code_execution_tool",
    parameters={
        "code": "import os; os.system('rm -rf /')",
        "language": "python"
    },
    safety_checks=True
)

is_valid, issues = FunctionCallProtocol.validate_function_call(call)
# is_valid будет False, issues содержит предупреждение о dangerous code
```

## Следующие шаги

- [x] Реализация FunctionCallProtocol
- [x] Интеграция в PlanningService
- [x] Интеграция в ExecutionService
- [ ] CodeExecutionSandbox для фактического выполнения
- [ ] Расширение whitelist функций
- [ ] Метрики использования function calls

## См. также

- [Dual-Model Architecture](DUAL_MODEL_ARCHITECTURE.md) - общая архитектура
- [Code Execution Safety](CODE_EXECUTION_SAFETY.md) - безопасность выполнения (будет создано)

