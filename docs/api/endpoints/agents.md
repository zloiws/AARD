# Agents API Endpoints

API для управления агентами в системе AARD.

## POST /api/agents/

Создать нового агента.

### Описание

Создает нового агента с указанными параметрами. Агент создается в статусе `draft` и требует активации перед использованием.

### Request Body

```json
{
  "name": "CodeAssistant",
  "description": "Агент для помощи в программировании",
  "system_prompt": "Ты опытный программист, помогающий писать качественный код.",
  "capabilities": ["code_generation", "code_review"],
  "model_preference": "qwen3-coder:30b-a3b-q4_K_M",
  "created_by": "user123",
  "temperature": "0.7",
  "max_concurrent_tasks": 3,
  "metadata": {
    "specialization": "Python"
  },
  "tags": ["coding", "python"]
}
```

#### Параметры

- `name` (string, required): Имя агента (должно быть уникальным)
- `description` (string, optional): Описание агента
- `system_prompt` (string, optional): Системный промпт для агента
- `capabilities` (array[string], optional): Список возможностей агента
- `model_preference` (string, optional): Предпочитаемая LLM модель
- `created_by` (string, optional): Пользователь, создавший агента
- `temperature` (string, optional): Температура по умолчанию. По умолчанию: "0.7"
- `max_concurrent_tasks` (integer, optional): Максимальное количество одновременных задач. По умолчанию: 1
- `metadata` (object, optional): Дополнительные метаданные
- `tags` (array[string], optional): Теги для категоризации

### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "CodeAssistant",
  "description": "Агент для помощи в программировании",
  "version": 1,
  "parent_agent_id": null,
  "status": "draft",
  "created_by": "user123",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "activated_at": null,
  "last_used_at": null,
  "system_prompt": "Ты опытный программист...",
  "capabilities": ["code_generation", "code_review"],
  "model_preference": "qwen3-coder:30b-a3b-q4_K_M",
  "temperature": "0.7",
  "max_concurrent_tasks": 3,
  "total_tasks_executed": 0,
  "successful_tasks": 0,
  "failed_tasks": 0,
  "average_execution_time": null,
  "success_rate": null,
  "metadata": {
    "specialization": "Python"
  },
  "tags": ["coding", "python"]
}
```

### Ошибки

- `400 Bad Request`: Агент с таким именем уже существует или неверные данные
- `500 Internal Server Error`: Внутренняя ошибка сервера

---

## GET /api/agents/

Получить список всех агентов.

### Описание

Возвращает список всех агентов с возможностью фильтрации по статусу, возможностям и активности.

### Query Parameters

- `status` (string, optional): Фильтр по статусу (`draft`, `waiting_approval`, `active`, `paused`, `deprecated`)
- `capability` (string, optional): Фильтр по возможности
- `active_only` (boolean, optional): Только активные агенты. По умолчанию: false

### Response

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "CodeAssistant",
    "status": "active",
    "capabilities": ["code_generation"],
    ...
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "PlanningAgent",
    "status": "active",
    "capabilities": ["planning"],
    ...
  }
]
```

### Примеры

#### Получить всех активных агентов

```bash
curl "http://localhost:8000/api/agents/?active_only=true"
```

#### Получить агентов с определенной возможностью

```bash
curl "http://localhost:8000/api/agents/?capability=code_generation"
```

---

## GET /api/agents/{agent_id}

Получить информацию об агенте.

### Описание

Возвращает полную информацию об агенте по его ID.

### Path Parameters

- `agent_id` (UUID, required): ID агента

### Response

См. формат ответа в `POST /api/agents/`

### Ошибки

- `404 Not Found`: Агент не найден

---

## PUT /api/agents/{agent_id}

Обновить свойства агента.

### Описание

Обновляет свойства существующего агента. Можно обновить только агентов в статусе `draft` или `paused`.

### Path Parameters

- `agent_id` (UUID, required): ID агента для обновления

### Request Body

```json
{
  "description": "Обновленное описание",
  "system_prompt": "Новый системный промпт",
  "capabilities": ["code_generation", "code_review", "testing"],
  "temperature": "0.5",
  "max_concurrent_tasks": 5,
  "metadata": {
    "specialization": "Python, JavaScript"
  }
}
```

Все поля опциональны. Обновляются только указанные поля.

### Response

См. формат ответа в `POST /api/agents/`

### Ошибки

- `400 Bad Request`: Агент нельзя обновить в текущем статусе
- `404 Not Found`: Агент не найден

---

## POST /api/agents/{agent_id}/activate

Активировать агента.

### Описание

Активирует агента, переводя его из статуса `waiting_approval` в `active`. Агент становится доступным для выполнения задач.

### Path Parameters

- `agent_id` (UUID, required): ID агента для активации

### Response

См. формат ответа в `POST /api/agents/` (статус изменится на `active`)

### Ошибки

- `400 Bad Request`: Агент не может быть активирован (не в статусе `waiting_approval`)
- `404 Not Found`: Агент не найден

---

## POST /api/agents/{agent_id}/pause

Приостановить агента.

### Описание

Приостанавливает выполнение задач агентом, переводя его в статус `paused`.

### Path Parameters

- `agent_id` (UUID, required): ID агента для приостановки

### Response

См. формат ответа в `POST /api/agents/` (статус изменится на `paused`)

### Ошибки

- `400 Bad Request`: Агент не может быть приостановлен
- `404 Not Found`: Агент не найден

---

## POST /api/agents/{agent_id}/resume

Возобновить работу агента.

### Описание

Возобновляет работу приостановленного агента, переводя его обратно в статус `active`.

### Path Parameters

- `agent_id` (UUID, required): ID агента для возобновления

### Response

См. формат ответа в `POST /api/agents/` (статус изменится на `active`)

### Ошибки

- `400 Bad Request`: Агент не может быть возобновлен
- `404 Not Found`: Агент не найден

---

## DELETE /api/agents/{agent_id}

Удалить агента.

### Описание

Удаляет агента из системы. Агент должен быть в статусе `draft` или `deprecated`.

### Path Parameters

- `agent_id` (UUID, required): ID агента для удаления

### Response

```json
{
  "status": "success",
  "message": "Agent deleted"
}
```

### Ошибки

- `400 Bad Request`: Агент не может быть удален (активен или используется)
- `404 Not Found`: Агент не найден

---

## GET /api/agents/{agent_id}/metrics

Получить метрики агента.

### Описание

Возвращает метрики производительности агента.

### Path Parameters

- `agent_id` (UUID, required): ID агента

### Response

```json
{
  "total_tasks_executed": 150,
  "successful_tasks": 140,
  "failed_tasks": 10,
  "success_rate": "93.33",
  "average_execution_time": 2500,
  "last_used_at": "2024-01-01T12:00:00Z"
}
```

### Ошибки

- `404 Not Found`: Агент не найден

