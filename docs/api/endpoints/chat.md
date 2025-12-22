# Chat API Endpoints

API для взаимодействия с чатом и LLM моделями.

## POST /api/chat/

Отправить сообщение и получить ответ от LLM.

### Описание

Отправляет сообщение пользователя в систему и получает ответ от LLM. Система автоматически выбирает подходящую модель на основе типа задачи:
- `code_generation` / `code_analysis`: использует модель для кодирования (qwen3-coder)
- `reasoning` / `planning`: использует модель для рассуждений (deepseek-r1)
- `general_chat`: использует общую модель (deepseek-r1)

Если `system_prompt` не предоставлен, система пытается получить активный системный промпт из базы данных.

### Request Body

```json
{
  "message": "Напиши функцию на Python для сортировки списка",
  "task_type": "code_generation",
  "model": null,
  "server_id": null,
  "temperature": 0.7,
  "stream": false,
  "session_id": null,
  "system_prompt": null
}
```

#### Параметры

- `message` (string, required): Сообщение пользователя
- `task_type` (string, optional): Тип задачи (`code_generation`, `reasoning`, `planning`, `general_chat`). По умолчанию: `general_chat`
- `model` (string, optional): Конкретная модель для использования (переопределяет выбор по task_type)
- `server_id` (string, optional): ID сервера Ollama из базы данных (требуется при указании model)
- `temperature` (float, optional): Температура для генерации (0.0-2.0). По умолчанию: 0.7
- `stream` (boolean, optional): Потоковая передача ответа. По умолчанию: false
- `session_id` (string, optional): ID сессии чата (если не указан, создается новая)
- `system_prompt` (string, optional): Системный промпт для модели

### Response

```json
{
  "response": "def sort_list(items):\n    return sorted(items)",
  "model": "qwen3-coder:30b-a3b-q4_K_M",
  "task_type": "code_generation",
  "duration_ms": 1234,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "650e8400-e29b-41d4-a716-446655440001",
  "reasoning": null,
  "workflow_id": "750e8400-e29b-41d4-a716-446655440002"
}
```

#### Поля ответа

- `response` (string): Ответ от LLM
- `model` (string): Использованная модель
- `task_type` (string): Тип задачи
- `duration_ms` (integer, optional): Время выполнения в миллисекундах
- `session_id` (string, optional): ID сессии чата
- `trace_id` (string, optional): ID трассировки для отладки
- `reasoning` (string, optional): Текст рассуждений, если модель поддерживает
- `workflow_id` (string, optional): ID workflow для отслеживания выполнения

### Примеры использования

#### Базовое использование

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Привет, как дела?",
    "task_type": "general_chat"
  }'
```

#### Генерация кода

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Напиши функцию для вычисления факториала",
    "task_type": "code_generation",
    "temperature": 0.3
  }'
```

#### С использованием сессии

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Продолжи предыдущую мысль",
    "task_type": "general_chat",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

### Ошибки

- `400 Bad Request`: Неверный формат запроса
- `500 Internal Server Error`: Ошибка при обработке запроса

---

## GET /api/chat/session/{session_id}

Получить историю чат-сессии.

### Описание

Возвращает полную историю сообщений для указанной сессии чата.

### Path Parameters

- `session_id` (string, required): ID сессии чата

### Response

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-01T12:00:00Z",
  "title": "Обсуждение проекта",
  "messages": [
    {
      "id": "660e8400-e29b-41d4-a716-446655440000",
      "role": "user",
      "content": "Привет",
      "model": null,
      "timestamp": "2024-01-01T12:00:00Z",
      "metadata": {}
    },
    {
      "id": "770e8400-e29b-41d4-a716-446655440000",
      "role": "assistant",
      "content": "Привет! Чем могу помочь?",
      "model": "deepseek-r1-abliterated:8b",
      "timestamp": "2024-01-01T12:00:01Z",
      "metadata": {
        "task_type": "general_chat"
      }
    }
  ]
}
```

### Ошибки

- `404 Not Found`: Сессия не найдена

---

## POST /api/chat/session

Создать новую чат-сессию.

### Описание

Создает новую сессию чата. Если `system_prompt` не предоставлен, система пытается получить активный системный промпт из базы данных.

### Query Parameters

- `title` (string, optional): Заголовок сессии
- `system_prompt` (string, optional): Системный промпт для сессии

### Response

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-01T12:00:00Z",
  "title": "Новая сессия",
  "system_prompt": "Ты полезный ассистент."
}
```

### Пример

```bash
curl -X POST "http://localhost:8000/api/chat/session?title=Мой%20чат" \
  -H "Content-Type: application/json"
```

---

## DELETE /api/chat/session/{session_id}

Удалить чат-сессию.

### Описание

Удаляет сессию чата и все связанные сообщения.

### Path Parameters

- `session_id` (string, required): ID сессии для удаления

### Response

```json
{
  "status": "success",
  "message": "Session 550e8400-e29b-41d4-a716-446655440000 deleted"
}
```

### Ошибки

- `404 Not Found`: Сессия не найдена
- `500 Internal Server Error`: Ошибка при удалении

---

## POST /api/chat/multi-model

Многомодельный чат - модели общаются друг с другом.

### Описание

Запускает диалог между несколькими LLM моделями. Модели по очереди отвечают друг другу.

### Request Body

```json
{
  "models": ["deepseek-r1-abliterated:8b", "qwen3-coder:30b-a3b-q4_K_M"],
  "initial_message": "Обсудите лучший способ сортировки данных",
  "system_prompts": {
    "deepseek-r1-abliterated:8b": "Ты эксперт по алгоритмам",
    "qwen3-coder:30b-a3b-q4_K_M": "Ты эксперт по программированию"
  },
  "max_turns": 10,
  "session_id": null
}
```

#### Параметры

- `models` (array[string], required): Список имен моделей для участия
- `initial_message` (string, required): Начальное сообщение для начала диалога
- `system_prompts` (object, optional): Системные промпты для каждой модели
- `max_turns` (integer, optional): Максимальное количество ходов (1-50). По умолчанию: 10
- `session_id` (string, optional): ID сессии чата

### Response

```json
{
  "status": "not_implemented",
  "message": "Multi-model chat coming soon"
}
```

**Примечание:** Данный endpoint находится в разработке.

