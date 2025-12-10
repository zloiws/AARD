# Tools API Endpoints

API для управления инструментами (tools) в системе AARD.

## POST /api/tools/

Создать новый инструмент.

### Описание

Создает новый инструмент, который может быть использован агентами для выполнения действий.

### Request Body

```json
{
  "name": "web_search",
  "description": "Поиск информации в интернете",
  "category": "web",
  "code": "def execute(query):\n    # Implementation\n    return results",
  "entry_point": "execute",
  "language": "python",
  "input_schema": {
    "type": "object",
    "properties": {
      "query": {"type": "string"}
    }
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "results": {"type": "array"}
    }
  },
  "dependencies": ["requests"],
  "requires_approval": false,
  "tags": ["web", "search"]
}
```

### Response

См. формат ответа в `GET /api/tools/{tool_id}`

---

## GET /api/tools/

Получить список всех инструментов.

### Query Parameters

- `status` (string, optional): Фильтр по статусу
- `category` (string, optional): Фильтр по категории
- `active_only` (boolean, optional): Только активные инструменты

---

## GET /api/tools/{tool_id}

Получить информацию об инструменте.

---

## PUT /api/tools/{tool_id}

Обновить инструмент.

---

## POST /api/tools/{tool_id}/activate

Активировать инструмент.

---

## POST /api/tools/{tool_id}/pause

Приостановить инструмент.

---

## DELETE /api/tools/{tool_id}

Удалить инструмент.

---

## GET /api/tools/{tool_id}/metrics

Получить метрики использования инструмента.

