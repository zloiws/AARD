# Настройка логирования

AARD поддерживает гибкую настройку логирования с возможностью установки отдельных уровней для каждого модуля.

## Общий уровень логирования

В файле `.env` можно установить общий уровень логирования для всего приложения:

```env
LOG_LEVEL=INFO
```

Доступные уровни: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Уровни логирования для отдельных модулей

### Способ 1: Через переменную окружения (статическая настройка)

В файле `.env` можно указать уровни логирования для конкретных модулей через переменную `LOG_MODULE_LEVELS`:

```env
LOG_MODULE_LEVELS={"app.api": "DEBUG", "app.services.planning_service": "DEBUG", "app.core.ollama_client": "WARNING"}
```

**Формат:** JSON строка с парами `"модуль": "уровень"`

**Примеры модулей:**
- `app` - весь модуль app
- `app.api` - все API endpoints
- `app.api.routes.chat` - только chat API
- `app.services` - все сервисы
- `app.services.planning_service` - сервис планирования
- `app.core.ollama_client` - клиент Ollama
- `sqlalchemy.engine` - SQLAlchemy запросы
- `uvicorn.access` - Uvicorn access логи
- `uvicorn.error` - Uvicorn error логи

**Пример полной настройки в `.env`:**

```env
# Общий уровень
LOG_LEVEL=INFO

# Уровни для конкретных модулей
LOG_MODULE_LEVELS={"app.api.routes.chat": "DEBUG", "app.services.planning_service": "DEBUG", "app.core.ollama_client": "WARNING", "sqlalchemy.engine": "WARNING"}
```

### Способ 2: Через API (динамическая настройка)

Можно изменять уровни логирования во время работы приложения через REST API.

#### Получить все уровни логирования

```bash
GET /api/logging/levels
```

**Ответ:**
```json
{
  "root": "INFO",
  "app": "INFO",
  "app.api": "DEBUG",
  "app.services": "INFO",
  "app.core": "INFO",
  "sqlalchemy.engine": "WARNING",
  "uvicorn.access": "WARNING",
  "uvicorn.error": "INFO"
}
```

#### Получить уровень для конкретного модуля

```bash
GET /api/logging/levels/{module}
```

**Пример:**
```bash
GET /api/logging/levels/app.api.routes.chat
```

**Ответ:**
```json
{
  "module": "app.api.routes.chat",
  "level": "DEBUG"
}
```

#### Установить уровень для модуля

```bash
PUT /api/logging/levels/{module}
Content-Type: application/json

{
  "level": "DEBUG"
}
```

**Пример:**
```bash
curl -X PUT http://localhost:8000/api/logging/levels/app.api.routes.chat \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG"}'
```

**Ответ:**
```json
{
  "module": "app.api.routes.chat",
  "level": "DEBUG"
}
```

**Валидные уровни:** `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`, `NOTSET`

## Дополнительные настройки логирования

### Формат логов

```env
# JSON формат (структурированное логирование)
LOG_FORMAT=json

# Текстовый формат (обычное логирование)
LOG_FORMAT=text
```

### Логирование SQLAlchemy

```env
# Включить логирование SQL запросов
LOG_SQLALCHEMY=true
```

### Логирование Uvicorn

```env
# Включить access логи Uvicorn
LOG_UVICORN_ACCESS=true
```

### Файловое логирование

```env
# Включить запись логов в файл
LOG_FILE_ENABLED=true

# Путь к файлу логов (относительно корня проекта)
LOG_FILE_PATH=logs/aard.log

# Ротация логов: 'midnight', 'W0' (еженедельно), или размер '10MB'
LOG_FILE_ROTATION=midnight

# Количество дней хранения логов
LOG_FILE_RETENTION=30
```

### Логирование чувствительных данных

⚠️ **ВНИМАНИЕ:** По умолчанию чувствительные данные (пароли, токены) маскируются в логах.

```env
# Включить логирование чувствительных данных (НЕ РЕКОМЕНДУЕТСЯ)
LOG_SENSITIVE_DATA=true
```

## Метрики логирования

### Получить метрики

```bash
GET /api/logging/metrics
```

**Ответ:**
```json
{
  "metrics": {
    "DEBUG": 150,
    "INFO": 500,
    "WARNING": 20,
    "ERROR": 5,
    "CRITICAL": 0
  },
  "total": 675
}
```

### Сбросить метрики

```bash
POST /api/logging/metrics/reset
```

## Примеры использования

### Пример 1: Отладка конкретного API endpoint

```bash
# Установить DEBUG для chat API
curl -X PUT http://localhost:8000/api/logging/levels/app.api.routes.chat \
  -H "Content-Type: application/json" \
  -d '{"level": "DEBUG"}'
```

### Пример 2: Отключить логирование SQLAlchemy

```bash
# Установить WARNING для SQLAlchemy
curl -X PUT http://localhost:8000/api/logging/levels/sqlalchemy.engine \
  -H "Content-Type: application/json" \
  -d '{"level": "WARNING"}'
```

### Пример 3: Настройка через .env для разработки

```env
LOG_LEVEL=INFO
LOG_MODULE_LEVELS={"app.api.routes.chat": "DEBUG", "app.services.planning_service": "DEBUG", "sqlalchemy.engine": "WARNING"}
LOG_FORMAT=json
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/aard.log
```

### Пример 4: Настройка для продакшена

```env
LOG_LEVEL=WARNING
LOG_MODULE_LEVELS={"app": "INFO", "sqlalchemy.engine": "ERROR", "uvicorn.access": "WARNING"}
LOG_FORMAT=json
LOG_FILE_ENABLED=true
LOG_FILE_PATH=logs/aard.log
LOG_FILE_RETENTION=90
```

## Структура модулей

Модули в AARD организованы следующим образом:

```
app/
├── api/
│   └── routes/          # app.api.routes.*
│       ├── chat.py      # app.api.routes.chat
│       ├── plans.py     # app.api.routes.plans
│       └── ...
├── services/            # app.services.*
│   ├── planning_service.py    # app.services.planning_service
│   ├── execution_service.py   # app.services.execution_service
│   └── ...
└── core/                # app.core.*
    ├── ollama_client.py       # app.core.ollama_client
    ├── logging_config.py      # app.core.logging_config
    └── ...
```

## Примечания

1. **Изменения через API** действуют только до перезапуска сервера. Для постоянных изменений используйте `.env`.

2. **Иерархия модулей:** Если установлен уровень для `app.api`, он применяется ко всем подмодулям, если для них не указан отдельный уровень.

3. **Производительность:** Уровень `DEBUG` может значительно увеличить объем логов и снизить производительность. Используйте его только для отладки.

4. **Безопасность:** Не включайте `LOG_SENSITIVE_DATA=true` в продакшене.

