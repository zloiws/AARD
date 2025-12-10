# Prompts API Endpoints

API для управления промптами в системе AARD.

## GET /api/prompts/

Получить список промптов.

### Query Parameters

- `prompt_type` (string, optional): Тип промпта
- `status` (string, optional): Статус промпта
- `level` (integer, optional): Уровень промпта
- `name` (string, optional): Поиск по имени
- `limit` (integer, optional): Максимум результатов. По умолчанию: 50
- `offset` (integer, optional): Смещение для пагинации. По умолчанию: 0

---

## GET /api/prompts/{prompt_id}

Получить промпт по ID.

---

## POST /api/prompts/

Создать новый промпт.

### Request Body

```json
{
  "name": "system_prompt_v1",
  "prompt_text": "Ты полезный ассистент...",
  "prompt_type": "system",
  "level": 0
}
```

---

## PUT /api/prompts/{prompt_id}

Обновить промпт.

---

## POST /api/prompts/{prompt_id}/version

Создать новую версию промпта.

---

## POST /api/prompts/{prompt_id}/deprecate

Пометить промпт как устаревший.

---

## GET /api/prompts/{prompt_id}/versions

Получить все версии промпта.

---

## GET /api/prompts/{prompt_id}/metrics

Получить метрики производительности промпта.

---

## GET /api/prompts/metrics/comparison

Сравнить метрики разных промптов.

---

## DELETE /api/prompts/{prompt_id}

Удалить промпт.

