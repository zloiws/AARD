# API Documentation

Полная документация REST API для AARD (Autonomous Agentic Recursive Development).

## Структура документации

- [Overview](overview.md) - Обзор API и общая информация
- [Chat API](endpoints/chat.md) - Чат и взаимодействие с LLM
- [Agents API](endpoints/agents.md) - Управление агентами
- [Plans API](endpoints/plans.md) - Управление планами задач
- [Tasks API](endpoints/tasks.md) - Управление задачами
- [Tools API](endpoints/tools.md) - Управление инструментами
- [Prompts API](endpoints/prompts.md) - Управление промптами
- [Models API](endpoints/models.md) - Управление моделями и серверами Ollama
- [Approvals API](endpoints/approvals.md) - Система утверждений
- [Workflow API](endpoints/workflow.md) - Workflow и события
- [Memory API](endpoints/memory.md) - Система памяти агентов
- [Benchmarks API](endpoints/benchmarks.md) - Benchmark система
- [Metrics API](endpoints/metrics.md) - Метрики и мониторинг
- [Health API](endpoints/health.md) - Health checks
- [Auth API](endpoints/auth.md) - Аутентификация и авторизация
- [Settings API](endpoints/settings.md) - Настройки системы

## Базовый URL

Все API endpoints доступны по базовому URL:
```
http://localhost:8000
```

## Формат ответов

Все API endpoints возвращают JSON, если не указано иное.

### Успешный ответ
```json
{
  "data": {...},
  "status": "success"
}
```

### Ошибка
```json
{
  "error": "Error message",
  "status": "error",
  "code": 400
}
```

## Аутентификация

Большинство endpoints требуют аутентификации. Используйте JWT токен в заголовке:
```
Authorization: Bearer <token>
```

## Rate Limiting

API имеет ограничения на количество запросов. При превышении лимита возвращается:
```json
{
  "error": "Rate limit exceeded",
  "status": "error",
  "code": 429
}
```

## Версионирование

Текущая версия API: **v1**

Все endpoints находятся под префиксом `/api/`.

