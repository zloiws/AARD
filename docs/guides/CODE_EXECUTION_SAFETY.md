# Code Execution Safety

## Обзор

CodeExecutionSandbox обеспечивает безопасное выполнение кода в изолированной среде с ограничениями ресурсов и проверками безопасности.

## Концепция

Вместо выполнения кода напрямую, система использует sandbox, который:
- Валидирует код перед выполнением
- Применяет ограничения ресурсов (timeout, memory)
- Изолирует выполнение
- Логирует все действия

## Основные возможности

### Валидация безопасности

Перед выполнением код проверяется на:
- Опасные импорты (`os.system`, `subprocess`, `eval`, `exec`)
- Доступ к файловой системе (`open`, `file`, `__file__`)
- Сетевой доступ (`socket`, `urllib`, `requests`)
- Другие потенциально опасные операции

### Ограничения ресурсов

- **Timeout**: Максимальное время выполнения (по умолчанию 30 секунд)
- **Memory Limit**: Ограничение памяти (по умолчанию 512 MB)
- **Output Size**: Максимальный размер вывода (10 MB)

### Изоляция

- Временные файлы для кода
- Отдельный процесс выполнения
- Очистка после выполнения

## Использование

### Базовое использование

```python
from app.services.code_execution_sandbox import CodeExecutionSandbox

sandbox = CodeExecutionSandbox()

result = sandbox.execute_code_safely(
    code="""
def add(a, b):
    return a + b

print(add(2, 3))
""",
    language="python"
)

print(result["status"])  # "success" or "error"
print(result["output"])  # Output from code execution
```

### С ограничениями

```python
result = sandbox.execute_code_safely(
    code="print('Hello, World!')",
    language="python",
    constraints={
        "timeout": 10,  # 10 seconds
        "memory_limit": 256  # 256 MB
    }
)
```

### Валидация перед выполнением

```python
validation = sandbox.validate_code_safety(
    code="import os; os.system('rm -rf /')",
    language="python"
)

if not validation["is_safe"]:
    print(f"Code is unsafe: {validation['issues']}")
```

## Интеграция с Function Calling

CodeExecutionSandbox автоматически интегрирован в ExecutionService для выполнения function calls:

```python
# В ExecutionService._execute_action_step:
if function_call.function == "code_execution_tool":
    sandbox = CodeExecutionSandbox()
    execution_result = sandbox.execute_code_safely(
        code=function_call.parameters["code"],
        language=function_call.parameters["language"],
        constraints={...}
    )
```

## Безопасность

### Блокируемые операции

- `os.system`, `subprocess` - системные вызовы
- `eval`, `exec`, `__import__` - динамическое выполнение
- `open`, `file` - доступ к файловой системе
- Сетевые операции

### Ограничения

- **Timeout**: Предотвращает бесконечные циклы
- **Memory Limit**: Предотвращает переполнение памяти
- **Output Limit**: Предотвращает огромные выводы

## Поддерживаемые языки

В настоящее время поддерживается:
- **Python** - полная поддержка

Планируется:
- JavaScript/Node.js
- Bash/Shell
- Другие языки

## Примеры

### Пример 1: Простое выполнение

```python
sandbox = CodeExecutionSandbox()
result = sandbox.execute_code_safely(
    code="x = 1 + 1\nprint(x)",
    language="python"
)
# result["status"] = "success"
# result["output"] = "2\n"
```

### Пример 2: Обработка ошибок

```python
result = sandbox.execute_code_safely(
    code="x = 1 / 0",
    language="python"
)
# result["status"] = "error"
# result["error"] = "ZeroDivisionError: division by zero"
```

### Пример 3: Блокировка опасного кода

```python
result = sandbox.execute_code_safely(
    code="import os; os.system('rm -rf /')",
    language="python"
)
# result["status"] = "error"
# result["error"] = "Code safety validation failed: ..."
```

### Пример 4: Timeout

```python
result = sandbox.execute_code_safely(
    code="import time; time.sleep(60)",
    language="python",
    constraints={"timeout": 2}
)
# result["status"] = "error"
# result["error"] = "Execution timeout after 2 seconds"
```

## Тестирование

```bash
python -m pytest tests/integration/test_code_sandbox.py -v
```

## Ограничения

### Windows

На Windows некоторые функции ограничены:
- `resource` модуль недоступен (только Unix)
- Memory limits могут работать иначе
- `preexec_fn` не поддерживается

### Изоляция

Текущая реализация использует:
- Отдельный процесс Python
- Временные файлы
- Timeout через subprocess

Для более строгой изоляции рекомендуется:
- Docker контейнеры
- Виртуальные машины
- Специализированные sandbox решения

## Следующие шаги

- [x] Реализация CodeExecutionSandbox
- [x] Интеграция в ExecutionService
- [ ] Поддержка дополнительных языков
- [ ] Docker-based изоляция
- [ ] Метрики выполнения
- [ ] Кэширование результатов

## См. также

- [Function Calling Protocol](FUNCTION_CALLING.md) - структурированные вызовы функций
- [Execution Service](../archive/PLAN_APPROVAL_INTEGRATION.md) - выполнение планов

