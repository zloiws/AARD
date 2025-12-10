# Справочник настроек AARD

**Всего настроек:** 33

## Feature Flags (5)

Включение/выключение основных функций системы.

| Ключ | Значение по умолчанию | Описание |
|------|----------------------|----------|
| `feature.agent_ops.enabled` | false | Операции агентов |
| `feature.a2a.enabled` | false | Agent-to-Agent коммуникация |
| `feature.planning.enabled` | false | Система планирования |
| `feature.tracing.enabled` | **true** | OpenTelemetry трассировка |
| `feature.caching.enabled` | **true** | Кэширование LLM ответов |

## Logging Levels (15)

Управление уровнями логирования глобально и для отдельных модулей.

### Глобальный

| Ключ | Значение по умолчанию | Описание |
|------|----------------------|----------|
| `logging.global.level` | WARNING | Глобальный уровень логирования |

### API Routes (4)

| Ключ | Значение | Назначение |
|------|----------|------------|
| `logging.module.app.api.routes.chat.level` | INFO | Чат API |
| `logging.module.app.api.routes.agents.level` | INFO | Агенты API |
| `logging.module.app.api.routes.plans.level` | INFO | Планы API |
| `logging.module.app.api.routes.benchmarks.level` | INFO | Бенчмарки API |

### Services (7)

| Ключ | Значение | Назначение |
|------|----------|------------|
| `logging.module.app.services.planning_service.level` | INFO | Сервис планирования |
| `logging.module.app.services.execution_service.level` | INFO | Сервис выполнения |
| `logging.module.app.services.agent_dialog_service.level` | **DEBUG** | Диалоги агентов (детальное логирование) |
| `logging.module.app.services.agent_service.level` | INFO | Управление агентами |
| `logging.module.app.services.tool_service.level` | INFO | Управление инструментами |
| `logging.module.app.services.memory_service.level` | INFO | Память агентов |
| `logging.module.app.services.workflow_event_service.level` | WARNING | События workflow |

### Core (3)

| Ключ | Значение | Назначение |
|------|----------|------------|
| `logging.module.app.core.ollama_client.level` | WARNING | Клиент Ollama |
| `logging.module.app.core.request_router.level` | INFO | Маршрутизация запросов |
| `logging.module.app.core.tracing.level` | WARNING | Трассировка |

## System Settings (13)

Системные параметры, управляемые через UI.

### LLM Settings (5)

Настройки взаимодействия с LLM.

| Ключ | По умолчанию | Диапазон | Описание |
|------|--------------|----------|----------|
| `system.llm.timeout_seconds` | 30 | 5-300 | Максимальное время ожидания ответа LLM |
| `system.llm.max_tokens` | **500** | 50-2000 | Максимум токенов в ответе (ограничение "думать час") |
| `system.llm.temperature` | 0.3 | 0.0-1.0 | Температура (ниже = детерминированнее) |
| `system.llm.top_p` | 0.8 | 0.0-1.0 | Top-p sampling |
| `system.llm.num_ctx` | 2048 | 512-8192 | Размер контекста в токенах |

### Planning Settings (2)

Настройки системы планирования.

| Ключ | По умолчанию | Диапазон | Описание |
|------|--------------|----------|----------|
| `system.planning.timeout_seconds` | 60 | 10-300 | Таймаут генерации плана |
| `system.planning.max_steps` | **10** | 1-50 | Максимум шагов в плане |

### Execution Settings (2)

Настройки выполнения планов.

| Ключ | По умолчанию | Диапазон | Описание |
|------|--------------|----------|----------|
| `system.execution.timeout_seconds` | 45 | 5-300 | Таймаут одного шага |
| `system.execution.max_total_timeout_seconds` | 180 | 30-600 | Максимальное время выполнения всего плана |

### Code Execution Settings (2)

Настройки sandbox для выполнения кода.

| Ключ | По умолчанию | Диапазон | Описание |
|------|--------------|----------|----------|
| `system.code_execution.timeout_seconds` | 30 | 5-120 | Таймаут выполнения кода |
| `system.code_execution.memory_limit_mb` | 256 | 64-1024 | Лимит памяти (MB) |

### Database Settings (2)

Настройки подключения к БД.

| Ключ | По умолчанию | Диапазон | Описание |
|------|--------------|----------|----------|
| `system.database.pool_size` | 20 | 1+ | Размер пула соединений |
| `system.database.max_overflow` | 10 | 0+ | Максимум overflow соединений |

## Рекомендации по настройке

### Для разработки

```
feature.planning.enabled = true
feature.agent_ops.enabled = true
logging.global.level = DEBUG
logging.module.app.services.planning_service.level = DEBUG
system.llm.timeout_seconds = 60  # больше времени для отладки
```

### Для production

```
feature.tracing.enabled = true
feature.caching.enabled = true
logging.global.level = WARNING
system.llm.timeout_seconds = 30
system.llm.max_tokens = 500  # ограничение для скорости
```

### Для тестирования

```
logging.global.level = INFO
logging.module.app.services.agent_dialog_service.level = DEBUG
system.planning.max_steps = 5  # меньше шагов для быстрых тестов
system.execution.timeout_seconds = 20
```

## Управление через UI

1. Откройте `http://localhost:8000/settings`
2. **Feature Flags** - переключатели вкл/выкл
3. **Logging Levels** - выпадающие списки уровней
4. **Module Settings** - редактируемые поля для системных параметров
5. Измените нужные настройки
6. Нажмите **"Apply Changes"** для сохранения

## Управление через API

```bash
# Получить все настройки
curl http://localhost:8000/api/settings/

# Получить feature flags
curl http://localhost:8000/api/settings/features/all

# Установить feature flag
curl -X POST http://localhost:8000/api/settings/features/ \
  -H "Content-Type: application/json" \
  -d '{"feature": "planning", "enabled": true}'

# Установить уровень логирования
curl -X POST http://localhost:8000/api/settings/logging/ \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG", "module": "app.services.planning_service"}'

# Обновить системную настройку
curl -X POST http://localhost:8000/api/settings/ \
  -H "Content-Type: application/json" \
  -d '{
    "key": "system.llm.max_tokens",
    "value": 1000,
    "category": "system",
    "value_type": "integer"
  }'
```

## Добавление новых настроек

1. Добавьте настройку в скрипт `backend/scripts/migrate_env_to_db.py`
2. Запустите миграцию: `python scripts/migrate_env_to_db.py`
3. Настройка появится в UI автоматически

Для системных настроек (редактируемых через UI):
- Категория должна быть `system`
- Укажите правильный `value_type` (integer, float, boolean, string)
- Добавьте описательный `description`

