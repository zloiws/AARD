# Глобальные ограничения ресурсов (стопоры)

## Цель

Обеспечить скорость и экономию ресурсов, предотвратить неограниченные размышления LLM и выполнение кода.

## Конфигурация

Все ограничения настраиваются в `backend/app/core/config.py` и могут быть переопределены через переменные окружения в `.env`:

### LLM Ограничения

```env
# Максимальное время ожидания ответа LLM (секунды)
LLM_TIMEOUT_SECONDS=30

# Максимальное количество токенов в ответе (ограничение "думать час")
LLM_MAX_TOKENS=500

# Температура LLM (низкая = быстрые детерминированные ответы)
LLM_TEMPERATURE=0.3

# Top-p для LLM (ограничение выборки)
LLM_TOP_P=0.8

# Размер контекста LLM (уменьшен для скорости)
LLM_NUM_CTX=2048
```

### Планирование

```env
# Максимальное время генерации плана (секунды)
PLANNING_TIMEOUT_SECONDS=60

# Максимальное количество шагов в плане
PLANNING_MAX_STEPS=10
```

### Выполнение

```env
# Максимальное время выполнения одного шага (секунды)
EXECUTION_TIMEOUT_SECONDS=45

# Максимальное время выполнения всего плана (секунды)
EXECUTION_MAX_TOTAL_TIMEOUT_SECONDS=180
```

### Выполнение кода (Sandbox)

```env
# Максимальное время выполнения кода (секунды)
CODE_EXECUTION_TIMEOUT_SECONDS=30

# Максимальное использование памяти (MB)
CODE_EXECUTION_MEMORY_LIMIT_MB=256

# Максимальный размер вывода (MB)
CODE_EXECUTION_MAX_OUTPUT_SIZE_MB=5

# Максимальное использование CPU (процент)
CODE_EXECUTION_CPU_LIMIT_PERCENT=50
```

## Применение

### OllamaClient

Все LLM вызовы через `OllamaClient.generate()` автоматически применяют:
- `llm_timeout_seconds` - таймаут запроса
- `llm_max_tokens` - ограничение длины ответа (num_predict)
- `llm_temperature` - температура по умолчанию
- `llm_top_p` - top-p по умолчанию
- `llm_num_ctx` - размер контекста

### PlanningService

- `planning_timeout_seconds` - таймаут для генерации плана
- `planning_max_steps` - максимальное количество шагов

### ExecutionService

- `execution_timeout_seconds` - таймаут для выполнения одного шага
- `execution_max_total_timeout_seconds` - общий таймаут выполнения всего плана (стопор)

### CodeExecutionSandbox

- `code_execution_timeout_seconds` - таймаут выполнения кода
- `code_execution_memory_limit_mb` - лимит памяти
- `code_execution_max_output_size_mb` - лимит размера вывода
- `code_execution_cpu_limit_percent` - лимит CPU

## Переопределение

Ограничения можно переопределить в конкретных вызовах через `kwargs`:

```python
# Переопределить таймаут для конкретного вызова
response = await ollama_client.generate(
    prompt="...",
    timeout=60,  # Переопределить глобальный таймаут
    num_predict=1000,  # Переопределить максимальное количество токенов
    temperature=0.5  # Переопределить температуру
)
```

## Логирование

При инициализации `CodeExecutionSandbox` логируются все примененные ограничения:

```
Code execution sandbox initialized with limits
  timeout_seconds: 30
  memory_limit_mb: 256
  max_output_size_mb: 5
  cpu_limit_percent: 50
```

## Важно

- Все ограничения применяются **по умолчанию** во всех местах проекта
- Цель: **скорость и экономия ресурсов**
- Нет неограниченным размышлениям LLM
- Все локально и ограниченно

