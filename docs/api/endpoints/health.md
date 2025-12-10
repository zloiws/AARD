# Health API Endpoints

API для проверки состояния системы.

## GET /health

Базовая проверка здоровья системы.

### Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "service": "AARD"
}
```

---

## GET /health/detailed

Детальная проверка здоровья всех компонентов.

### Response

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "service": "AARD",
  "version": "0.1.0",
  "environment": "development",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "ollama_servers": {
      "status": "healthy",
      "message": "All 2 servers are available",
      "servers": [
        {
          "id": "...",
          "name": "Server 1",
          "reachable": true
        }
      ]
    }
  }
}
```

---

## GET /health/readiness

Проверка готовности системы к работе.

---

## GET /health/liveness

Проверка жизнеспособности системы.

