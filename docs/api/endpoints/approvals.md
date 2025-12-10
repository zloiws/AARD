# Approvals API Endpoints

API для управления запросами на утверждение.

## GET /api/approvals/

Получить список ожидающих утверждения запросов.

### Query Parameters

- `request_type` (string, optional): Тип запроса
- `limit` (integer, optional): Максимум результатов. По умолчанию: 50

### Response

```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "request_type": "agent_creation",
    "status": "pending",
    "artifact_id": null,
    "prompt_id": null,
    "task_id": null,
    "recommendation": "Рекомендуется утвердить",
    "risk_assessment": {
      "risk_level": "low",
      "factors": []
    },
    "created_at": "2024-01-01T12:00:00Z",
    "decision_timeout": "2024-01-02T12:00:00Z"
  }
]
```

---

## GET /api/approvals/{request_id}

Получить запрос на утверждение по ID.

---

## POST /api/approvals/{request_id}/approve

Утвердить запрос.

### Request Body

```json
{
  "feedback": "Одобрено"
}
```

---

## POST /api/approvals/{request_id}/reject

Отклонить запрос.

### Request Body

```json
{
  "feedback": "Причина отклонения"
}
```

---

## POST /api/approvals/{request_id}/modify

Изменить запрос перед утверждением.

### Request Body

```json
{
  "modified_data": {
    "name": "Измененное имя"
  },
  "feedback": "Комментарий"
}
```

