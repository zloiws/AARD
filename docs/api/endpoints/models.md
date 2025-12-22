# Models API Endpoints

API для управления моделями и серверами Ollama.

## GET /api/models/servers

Получить список серверов Ollama с доступными моделями.

### Response

```json
{
  "servers": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Ollama Server 1",
      "url": "http://10.39.0.101:11434",
      "api_url": "http://10.39.0.101:11434/v1",
      "version": "0.1.0",
      "available": true,
      "is_default": true,
      "models": [
        {
          "name": "deepseek-r1-abliterated:8b",
          "model": "deepseek-r1-abliterated:8b",
          "size": 5000000000,
          "digest": "sha256:...",
          "modified_at": "2024-01-01T12:00:00Z"
        }
      ]
    }
  ]
}
```

---

## GET /api/models/server/models

Получить модели с конкретного сервера по URL.

### Query Parameters

- `server_url` (string, required): URL сервера Ollama

---

## GET /api/servers/

Получить список всех серверов Ollama.

### Query Parameters

- `active_only` (boolean, optional): Только активные серверы

---

## POST /api/servers/

Создать новый сервер Ollama.

### Request Body

```json
{
  "name": "New Ollama Server",
  "url": "http://10.39.0.102:11434",
  "api_version": "v1",
  "description": "Описание сервера",
  "capabilities": ["general", "reasoning"],
  "max_concurrent": 2,
  "priority": 1,
  "is_default": false
}
```

---

## GET /api/servers/{server_id}

Получить информацию о сервере.

---

## PUT /api/servers/{server_id}

Обновить сервер.

---

## DELETE /api/servers/{server_id}

Удалить сервер.

---

## POST /api/servers/{server_id}/discover

Обнаружить модели на сервере.

---

## GET /api/servers/{server_id}/models

Получить список моделей на сервере.

---

## GET /api/models/{model_id}

Получить информацию о модели.

---

## PUT /api/models/{model_id}

Обновить модель.

---

## POST /api/models/{model_id}/check-availability

Проверить доступность модели.

---

## POST /api/models/{model_id}/unload

Выгрузить модель из памяти.

---

## POST /api/models/{model_id}/unload-from-gpu

Выгрузить модель из GPU.

