# Workflow API Endpoints

API для управления workflow и отслеживания выполнения задач.

## GET /api/workflow/current

Получить текущий процесс выполнения workflow.

### Описание

Возвращает текущие события workflow из WorkflowTracker и базы данных для активных задач.

### Response

```json
{
  "workflow_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "current_stage": "execution",
  "events": [
    {
      "stage": "planning",
      "message": "Создание плана...",
      "details": {},
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ]
}
```

---

## GET /api/workflow/recent

Получить недавние события workflow.

---

## GET /api/workflow/{workflow_id}

Получить все события для конкретного workflow.

### Path Parameters

- `workflow_id` (string, required): ID workflow

### Response

```json
[
  {
    "stage": "user_request",
    "message": "Запрос пользователя",
    "details": {},
    "timestamp": "2024-01-01T12:00:00Z"
  }
]
```

