# Интеграция с Ollama

## Обзор

Система поддерживает работу с несколькими инстансами Ollama одновременно. Клиент автоматически выбирает подходящую модель на основе типа задачи.

## Архитектура

### Компоненты

1. **OllamaClient** (`backend/app/core/ollama_client.py`)
   - Управление несколькими инстансами Ollama
   - Выбор модели на основе типа задачи
   - Кэширование ответов
   - Retry логика и обработка ошибок
   - Health checks

2. **ModelSelector** (`backend/app/core/model_selector.py`)
   - Специализированный выбор моделей для dual-model архитектуры
   - Разделение моделей планирования (reasoning) и генерации кода (code_generation)
   - Автоматический fallback при отсутствии специализированных моделей
   - Поддержка выбора по capabilities

3. **Chat API** (`backend/app/api/routes/chat.py`)
   - REST API для взаимодействия с LLM
   - Поддержка разных типов задач
   - Выбор модели по типу задачи

## Типы задач

Система поддерживает следующие типы задач:

- `code_generation` - Генерация кода → использует модель для кодирования (qwen3-coder)
- `code_analysis` - Анализ кода → использует модель для кодирования
- `reasoning` - Рассуждения → использует модель для рассуждений (deepseek-r1)
- `general_chat` - Обычный чат → использует общую модель (deepseek-r1)
- `planning` - Планирование → использует модель для рассуждений
- `text_generation` - Генерация текста → использует общую модель

## Конфигурация

В `.env` файле настроены два инстанса:

```env
# Ollama Instance 1 (General/Reasoning)
OLLAMA_URL_1=http://10.39.0.101:11434/v1
OLLAMA_MODEL_1=huihui_ai/deepseek-r1-abliterated:8b
OLLAMA_CAPABILITIES_1=general,reasoning,conversation
OLLAMA_MAX_CONCURRENT_1=2

# Ollama Instance 2 (Coding)
OLLAMA_URL_2=http://10.39.0.6:11434/v1
OLLAMA_MODEL_2=qwen3-coder:30b-a3b-q4_K_M
OLLAMA_CAPABILITIES_2=coding,code_generation,code_analysis
OLLAMA_MAX_CONCURRENT_2=1
```

## API Endpoints

### POST /api/chat/

Отправить сообщение и получить ответ от LLM.

**Request:**
```json
{
  "message": "Напиши функцию на Python",
  "task_type": "code_generation",
  "temperature": 0.7,
  "model": null  // опционально, переопределяет task_type
}
```

**Response:**
```json
{
  "response": "def my_function():\n    pass",
  "model": "qwen3-coder:30b-a3b-q4_K_M",
  "task_type": "code_generation",
  "duration_ms": 1234
}
```

### GET /api/chat/models

Получить список доступных моделей.

**Response:**
```json
{
  "models": [
    {
      "model": "huihui_ai/deepseek-r1-abliterated:8b",
      "url": "http://10.39.0.101:11434/v1",
      "capabilities": ["general", "reasoning", "conversation"],
      "max_concurrent": 2
    },
    {
      "model": "qwen3-coder:30b-a3b-q4_K_M",
      "url": "http://10.39.0.6:11434/v1",
      "capabilities": ["coding", "code_generation", "code_analysis"],
      "max_concurrent": 1
    }
  ]
}
```

## Использование в коде

### Базовое использование

```python
from app.core.ollama_client import get_ollama_client, TaskType

client = get_ollama_client()

# Генерация ответа
response = await client.generate(
    prompt="Напиши функцию на Python",
    task_type=TaskType.CODE_GENERATION,
    temperature=0.7
)

print(response.response)
```

### Выбор конкретной модели

```python
response = await client.generate(
    prompt="Помоги с задачей",
    model="qwen3-coder:30b-a3b-q4_K_M"  # Использует указанную модель
)
```

### Stream ответа

```python
async for chunk in client.generate_stream(
    prompt="Расскажи историю",
    task_type=TaskType.GENERAL_CHAT
):
    print(chunk.response, end="", flush=True)
```

## Кэширование

Система автоматически кэширует ответы на основе:
- Промпта
- Модели
- Параметров (temperature, top_p, etc.)

Кэш хранится 24 часа (настраивается через `OLLAMA_CACHING_TTL_HOURS`).

Отключение кэширования:
```env
ENABLE_CACHING=false
```

## Обработка ошибок

Клиент автоматически:
- Проверяет доступность инстансов (health check)
- Использует fallback на другой инстанс при недоступности
- Повторяет запросы при временных ошибках (до 3 попыток)
- Обрабатывает таймауты (5 минут)

## Health Checks

Перед использованием модели клиент проверяет её доступность:

```python
is_healthy = await client.health_check(instance)
```

При недоступности основной модели автоматически выбирается fallback.

## Производительность

- **Connection Pooling**: Используется пул соединений для каждого инстанса
- **Async/Await**: Все запросы асинхронные
- **Concurrent Requests**: Учитывается `max_concurrent` для каждого инстанса
- **Caching**: Кэширование снижает нагрузку на LLM

## Тестирование

```bash
# Тест клиента
python backend/test_ollama_integration.py

# Тест API
python backend/test_chat_api.py
```

## Следующие шаги

- [ ] Streaming responses через WebSocket
- [ ] Batch processing для множественных запросов
- [ ] Метрики и мониторинг использования моделей
- [ ] Динамическая загрузка моделей
- [ ] A/B тестирование моделей

