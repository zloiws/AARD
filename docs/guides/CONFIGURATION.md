# Конфигурация AARD

## Обзор

AARD использует переменные окружения для конфигурации. Все настройки определяются в файле `.env` в корне проекта.

## Основные настройки

### База данных

```env
POSTGRES_HOST=10.39.0.101
POSTGRES_DB=aard
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5432
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10
```

### Ollama

```env
# Ollama Instance 1
OLLAMA_URL_1=http://10.39.0.101:11434/v1
OLLAMA_MODEL_1=huihui_ai/deepseek-r1-abliterated:8b
OLLAMA_CAPABILITIES_1=general,reasoning,conversation
OLLAMA_MAX_CONCURRENT_1=2

# Ollama Instance 2
OLLAMA_URL_2=http://10.39.0.6:11434/v1
OLLAMA_MODEL_2=qwen3-coder:30b-a3b-q4_K_M
OLLAMA_CAPABILITIES_2=coding,code_generation,code_analysis
OLLAMA_MAX_CONCURRENT_2=1
```

### Приложение

```env
APP_NAME=AARD
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key_here
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=http://localhost:8000
```

## Автоматическое перепланирование

Настройки для автоматического перепланирования при ошибках:

```env
# Включить/выключить автоматическое перепланирование
ENABLE_AUTO_REPLANNING=true

# Максимальное количество попыток перепланирования на задачу
AUTO_REPLANNING_MAX_ATTEMPTS=3

# Минимальный интервал между попытками перепланирования (секунды)
AUTO_REPLANNING_MIN_INTERVAL_SECONDS=5

# Таймаут для каждой попытки перепланирования (секунды)
AUTO_REPLANNING_TIMEOUT_SECONDS=300

# Запускать перепланирование для CRITICAL ошибок
AUTO_REPLANNING_TRIGGER_CRITICAL=true

# Запускать перепланирование для HIGH ошибок
AUTO_REPLANNING_TRIGGER_HIGH=true

# Запускать перепланирование для MEDIUM ошибок
AUTO_REPLANNING_TRIGGER_MEDIUM=false

# Требовать вмешательство человека после N неудачных попыток
AUTO_REPLANNING_REQUIRE_HUMAN_INTERVENTION_AFTER=5
```

### Описание настроек

- **ENABLE_AUTO_REPLANNING** (по умолчанию: `true`)
  - Включает или выключает автоматическое перепланирование при ошибках

- **AUTO_REPLANNING_MAX_ATTEMPTS** (по умолчанию: `3`, диапазон: 1-10)
  - Максимальное количество попыток перепланирования для одной задачи
  - После достижения лимита перепланирование прекращается

- **AUTO_REPLANNING_MIN_INTERVAL_SECONDS** (по умолчанию: `5`, минимум: 0)
  - Минимальный интервал между попытками перепланирования
  - Предотвращает слишком частые попытки

- **AUTO_REPLANNING_TIMEOUT_SECONDS** (по умолчанию: `300`, минимум: 30)
  - Таймаут для каждой попытки перепланирования
  - Если перепланирование занимает больше времени, оно отменяется

- **AUTO_REPLANNING_TRIGGER_CRITICAL** (по умолчанию: `true`)
  - Запускать перепланирование для ошибок с критичностью CRITICAL

- **AUTO_REPLANNING_TRIGGER_HIGH** (по умолчанию: `true`)
  - Запускать перепланирование для ошибок с критичностью HIGH

- **AUTO_REPLANNING_TRIGGER_MEDIUM** (по умолчанию: `false`)
  - Запускать перепланирование для ошибок с критичностью MEDIUM
  - По умолчанию отключено, так как MEDIUM ошибки обычно не требуют перепланирования

- **AUTO_REPLANNING_REQUIRE_HUMAN_INTERVENTION_AFTER** (по умолчанию: `5`, минимум: 1)
  - После указанного количества попыток система будет требовать вмешательства человека
  - Используется для предотвращения бесконечных циклов перепланирования

## Логирование

```env
LOG_SQLALCHEMY=false
LOG_UVICORN_ACCESS=false
LOG_FORMAT=json
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/aard.log
LOG_FILE_ROTATION=midnight
LOG_FILE_RETENTION=30
LOG_SENSITIVE_DATA=false
```

## Tracing

```env
ENABLE_TRACING=true
TRACING_SERVICE_NAME=aard
TRACING_EXPORTER=console
TRACING_OTLP_ENDPOINT=
```

## Функциональность

```env
ENABLE_AGENT_OPS=false
ENABLE_A2A=false
ENABLE_PLANNING=false
ENABLE_CACHING=true
```

## Пример полного .env файла

```env
# Application
APP_NAME=AARD
APP_ENV=development
LOG_LEVEL=INFO
SECRET_KEY=your_secret_key_here
API_HOST=0.0.0.0
API_PORT=8000
ALLOWED_ORIGINS=http://localhost:8000

# Database
POSTGRES_HOST=10.39.0.101
POSTGRES_DB=aard
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_PORT=5432
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Ollama Instance 1
OLLAMA_URL_1=http://10.39.0.101:11434/v1
OLLAMA_MODEL_1=huihui_ai/deepseek-r1-abliterated:8b
OLLAMA_CAPABILITIES_1=general,reasoning,conversation
OLLAMA_MAX_CONCURRENT_1=2

# Ollama Instance 2
OLLAMA_URL_2=http://10.39.0.6:11434/v1
OLLAMA_MODEL_2=qwen3-coder:30b-a3b-q4_K_M
OLLAMA_CAPABILITIES_2=coding,code_generation,code_analysis
OLLAMA_MAX_CONCURRENT_2=1

# Automatic Replanning
ENABLE_AUTO_REPLANNING=true
AUTO_REPLANNING_MAX_ATTEMPTS=3
AUTO_REPLANNING_MIN_INTERVAL_SECONDS=5
AUTO_REPLANNING_TIMEOUT_SECONDS=300
AUTO_REPLANNING_TRIGGER_CRITICAL=true
AUTO_REPLANNING_TRIGGER_HIGH=true
AUTO_REPLANNING_TRIGGER_MEDIUM=false
AUTO_REPLANNING_REQUIRE_HUMAN_INTERVENTION_AFTER=5

# Features
ENABLE_TRACING=true
ENABLE_CACHING=true
```

## Использование в коде

```python
from app.core.config import get_settings

settings = get_settings()

# Проверка настроек
if settings.enable_auto_replanning:
    # Логика перепланирования
    if replan_count < settings.auto_replanning_max_attempts:
        # Перепланирование разрешено
        pass
```

## Валидация

Все настройки валидируются при загрузке. Неправильные значения приведут к ошибке при запуске приложения.

### Валидация числовых значений

- `AUTO_REPLANNING_MAX_ATTEMPTS`: 1-10
- `AUTO_REPLANNING_MIN_INTERVAL_SECONDS`: >= 0
- `AUTO_REPLANNING_TIMEOUT_SECONDS`: >= 30
- `AUTO_REPLANNING_REQUIRE_HUMAN_INTERVENTION_AFTER`: >= 1

## Дополнительная информация

- Подробнее о автоматическом перепланировании: [docs/guides/AUTOMATIC_REPLANNING.md](guides/AUTOMATIC_REPLANNING.md)
- Об обнаружении ошибок: [docs/EXECUTION_ERROR_DETECTION.md](../EXECUTION_ERROR_DETECTION.md)

