# Plans API Endpoints

API для управления планами выполнения задач.

## POST /api/plans/

Создать новый план для задачи.

### Описание

Создает новый план для выполнения задачи. План генерируется автоматически на основе описания задачи с использованием LLM.

### Request Body

```json
{
  "task_description": "Создать веб-приложение для управления задачами",
  "task_id": null,
  "context": {
    "priority": "high",
    "deadline": "2024-12-31"
  }
}
```

#### Параметры

- `task_description` (string, required): Описание задачи
- `task_id` (UUID, optional): ID существующей задачи для привязки плана
- `context` (object, optional): Дополнительный контекст для планирования

### Response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": "660e8400-e29b-41d4-a716-446655440001",
  "version": 1,
  "goal": "Создать веб-приложение для управления задачами",
  "strategy": {
    "approach": "iterative",
    "technologies": ["React", "FastAPI", "PostgreSQL"]
  },
  "steps": [
    {
      "step_number": 1,
      "description": "Создать структуру проекта",
      "agent_id": null,
      "tool_id": null,
      "dependencies": [],
      "estimated_duration": 3600
    },
    {
      "step_number": 2,
      "description": "Настроить базу данных",
      "agent_id": null,
      "tool_id": null,
      "dependencies": [1],
      "estimated_duration": 1800
    }
  ],
  "alternatives": null,
  "status": "draft",
  "current_step": 0,
  "estimated_duration": 14400,
  "actual_duration": null,
  "created_at": "2024-01-01T12:00:00Z",
  "approved_at": null,
  "model_logs": [
    {
      "timestamp": "2024-01-01T12:00:01Z",
      "model": "deepseek-r1-abliterated:8b",
      "prompt": "...",
      "response": "..."
    }
  ]
}
```

### Ошибки

- `400 Bad Request`: Неверный формат запроса
- `500 Internal Server Error`: Ошибка при создании плана

---

## GET /api/plans/

Получить список планов.

### Описание

Возвращает список планов с возможностью фильтрации по задаче и статусу.

### Query Parameters

- `task_id` (UUID, optional): Фильтр по ID задачи
- `status` (string, optional): Фильтр по статусу (`draft`, `pending_approval`, `approved`, `in_progress`, `completed`, `failed`, `cancelled`)
- `limit` (integer, optional): Максимальное количество результатов. По умолчанию: 100

### Response

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": "660e8400-e29b-41d4-a716-446655440001",
    "version": 1,
    "goal": "Создать веб-приложение",
    "status": "approved",
    ...
  }
]
```

### Примеры

#### Получить планы для задачи

```bash
curl "http://localhost:8000/api/plans/?task_id=660e8400-e29b-41d4-a716-446655440001"
```

#### Получить только утвержденные планы

```bash
curl "http://localhost:8000/api/plans/?status=approved"
```

---

## GET /api/plans/{plan_id}

Получить план по ID.

### Описание

Возвращает полную информацию о плане, включая все шаги и метаданные.

### Path Parameters

- `plan_id` (UUID, required): ID плана

### Response

См. формат ответа в `POST /api/plans/`

### Ошибки

- `404 Not Found`: План не найден

---

## PUT /api/plans/{plan_id}

Обновить план.

### Описание

Обновляет план. Можно обновлять только планы в статусе `draft`.

### Path Parameters

- `plan_id` (UUID, required): ID плана для обновления

### Request Body

```json
{
  "goal": "Обновленная цель",
  "strategy": {
    "approach": "agile"
  },
  "steps": [
    {
      "step_number": 1,
      "description": "Обновленный шаг",
      "dependencies": []
    }
  ]
}
```

Все поля опциональны.

### Response

См. формат ответа в `POST /api/plans/`

### Ошибки

- `400 Bad Request`: План нельзя обновить в текущем статусе
- `404 Not Found`: План не найден

---

## POST /api/plans/{plan_id}/approve

Утвердить план.

### Описание

Утверждает план, переводя его из статуса `pending_approval` в `approved`. После утверждения план может быть выполнен.

### Path Parameters

- `plan_id` (UUID, required): ID плана для утверждения

### Response

См. формат ответа в `POST /api/plans/` (статус изменится на `approved`)

### Ошибки

- `400 Bad Request`: План не может быть утвержден (не в статусе `pending_approval`)
- `404 Not Found`: План не найден

---

## POST /api/plans/{plan_id}/execute

Выполнить план.

### Описание

Запускает выполнение утвержденного плана. План переходит в статус `in_progress` и начинает выполняться по шагам.

### Path Parameters

- `plan_id` (UUID, required): ID плана для выполнения

### Response

См. формат ответа в `POST /api/plans/` (статус изменится на `in_progress`)

### Ошибки

- `400 Bad Request`: План не может быть выполнен (не утвержден или уже выполняется)
- `404 Not Found`: План не найден

---

## POST /api/plans/{plan_id}/replan

Перепланировать задачу.

### Описание

Создает новый план для задачи на основе причины перепланирования. Используется при ошибках выполнения или изменении требований.

### Path Parameters

- `plan_id` (UUID, required): ID текущего плана

### Request Body

```json
{
  "reason": "Текущий план не учитывает новые требования",
  "context": {
    "new_requirements": "Добавить поддержку мобильных устройств"
  }
}
```

#### Параметры

- `reason` (string, required): Причина перепланирования
- `context` (object, optional): Дополнительный контекст для нового плана

### Response

См. формат ответа в `POST /api/plans/` (новый план)

### Ошибки

- `400 Bad Request`: Неверный формат запроса
- `404 Not Found`: План не найден
- `500 Internal Server Error`: Ошибка при перепланировании

---

## GET /api/plans/{plan_id}/status

Получить статус выполнения плана.

### Описание

Возвращает текущий статус плана и прогресс выполнения.

### Path Parameters

- `plan_id` (UUID, required): ID плана

### Response

```json
{
  "status": "in_progress",
  "current_step": 3,
  "total_steps": 10,
  "progress_percent": 30.0,
  "estimated_remaining_time": 7200
}
```

---

## GET /api/plans/{plan_id}/quality

Оценить качество плана.

### Описание

Возвращает оценку качества плана на основе метрик.

### Path Parameters

- `plan_id` (UUID, required): ID плана

### Response

```json
{
  "quality_score": 0.85,
  "metrics": {
    "completeness": 0.9,
    "feasibility": 0.8,
    "efficiency": 0.85
  }
}
```

---

## GET /api/plans/statistics

Получить статистику по планам.

### Описание

Возвращает общую статистику по всем планам в системе.

### Response

```json
{
  "total_plans": 150,
  "by_status": {
    "draft": 10,
    "pending_approval": 5,
    "approved": 20,
    "in_progress": 15,
    "completed": 90,
    "failed": 10
  },
  "average_duration": 3600,
  "success_rate": 0.9
}
```

---

## POST /api/plans/{plan_id}/pause

Приостановить выполнение плана.

### Описание

Приостанавливает выполнение плана, переводя его в статус `paused`.

### Path Parameters

- `plan_id` (UUID, required): ID плана

### Response

См. формат ответа в `POST /api/plans/` (статус изменится на `paused`)

---

## POST /api/plans/{plan_id}/resume

Возобновить выполнение плана.

### Описание

Возобновляет выполнение приостановленного плана.

### Path Parameters

- `plan_id` (UUID, required): ID плана

### Response

См. формат ответа в `POST /api/plans/` (статус изменится на `in_progress`)

---

## GET /api/plans/{plan_id}/tree

Получить дерево зависимостей плана.

### Описание

Возвращает визуализацию зависимостей между шагами плана в виде дерева.

### Path Parameters

- `plan_id` (UUID, required): ID плана

### Response

```json
{
  "plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "tree": {
    "step_1": {
      "description": "Шаг 1",
      "dependencies": [],
      "children": ["step_2", "step_3"]
    },
    "step_2": {
      "description": "Шаг 2",
      "dependencies": ["step_1"],
      "children": ["step_4"]
    }
  }
}
```

---

## GET /api/plans/{plan_id}/alternatives

Получить альтернативные планы.

### Описание

Возвращает список альтернативных планов, если они были сгенерированы при создании.

### Path Parameters

- `plan_id` (UUID, required): ID плана

### Response

```json
{
  "main_plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "alternatives": [
    {
      "plan_id": "660e8400-e29b-41d4-a716-446655440001",
      "goal": "Альтернативный подход",
      "evaluation_score": 0.75,
      "differences": ["Использует другой стек технологий"]
    }
  ]
}
```

---

## GET /api/plans/{plan_id}/execution-state

Получить состояние выполнения плана.

### Описание

Возвращает детальное состояние выполнения плана, включая статус каждого шага.

### Path Parameters

- `plan_id` (UUID, required): ID плана

### Response

```json
{
  "plan_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "current_step": 3,
  "steps": [
    {
      "step_number": 1,
      "status": "completed",
      "result": "Шаг выполнен успешно",
      "duration": 1200
    },
    {
      "step_number": 2,
      "status": "completed",
      "result": "Шаг выполнен успешно",
      "duration": 800
    },
    {
      "step_number": 3,
      "status": "in_progress",
      "result": null,
      "duration": null
    }
  ]
}
```

