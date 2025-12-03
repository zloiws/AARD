# OpenTelemetry Tracing Implementation - Complete

## Реализованные компоненты

### 1. Базовая настройка OpenTelemetry SDK
- ✅ Создан модуль `backend/app/core/tracing.py` для конфигурации трассировки
- ✅ Поддержка трех типов экспортеров:
  - `console` - вывод в консоль (по умолчанию)
  - `otlp` - экспорт в OTLP endpoint
  - `database` - сохранение в PostgreSQL
- ✅ Автоматическая инструментация:
  - FastAPI (через `FastAPIInstrumentor`)
  - SQLAlchemy (через `SQLAlchemyInstrumentor`)
  - HTTPX (через `HTTPXClientInstrumentor`)
  - AioHTTP (через `AioHttpClientInstrumentor`)

### 2. Модель данных для трассировок
- ✅ Создана модель `ExecutionTrace` (`backend/app/models/trace.py`)
- ✅ Миграция `005_add_execution_traces.py` для создания таблицы
- ✅ Индексы для эффективного поиска:
  - По `trace_id`, `task_id`, `plan_id`
  - По `agent_id`, `tool_id`
  - По `start_time`, `status`, `operation_name`

### 3. Database Exporter
- ✅ Создан `DatabaseSpanExporter` (`backend/app/core/trace_exporter.py`)
- ✅ Автоматическое сохранение spans в БД
- ✅ Извлечение метаданных (task_id, plan_id, agent_id, tool_id) из атрибутов
- ✅ Обработка ошибок и статусов

### 4. Кастомные spans в критичных операциях
- ✅ **Planning Service**:
  - `planning.generate_plan` - генерация плана
  - `planning.analyze_task` - анализ задачи
  - `planning.decompose_task` - декомпозиция задачи
- ✅ **Execution Service**:
  - `execution.execute_step` - выполнение шага плана
- ✅ **Ollama Client**:
  - `ollama.generate` - запросы к LLM

### 5. Интеграция с логированием
- ✅ Автоматическое извлечение `trace_id` из OpenTelemetry context
- ✅ Добавление `trace_id` в контекст логирования
- ✅ Middleware автоматически связывает логи и трассировки

### 6. API для просмотра трассировок
- ✅ `GET /api/traces/` - список трассировок с фильтрами
- ✅ `GET /api/traces/{trace_id}` - детали трассировки
- ✅ `GET /api/traces/{trace_id}/spans` - все spans трассировки
- ✅ `GET /api/traces/stats/summary` - статистика трассировок

## Настройки в config.py

Добавлены новые параметры:
- `enable_tracing: bool = True` - включить/выключить трассировку
- `tracing_service_name: str = "aard"` - имя сервиса
- `tracing_exporter: str = "console"` - тип экспортера
- `tracing_otlp_endpoint: Optional[str] = None` - OTLP endpoint URL

## Использование

### Включение database экспортера

В `.env`:
```env
ENABLE_TRACING=true
TRACING_EXPORTER=database
TRACING_SERVICE_NAME=aard
```

### Включение OTLP экспортера

В `.env`:
```env
ENABLE_TRACING=true
TRACING_EXPORTER=otlp
TRACING_OTLP_ENDPOINT=http://localhost:4318/v1/traces
```

### Применение миграции

```bash
cd backend
alembic upgrade head
```

## Следующие шаги

1. Применить миграцию для создания таблицы `execution_traces`
2. Протестировать трассировку на реальных запросах
3. Создать веб-интерфейс для визуализации трассировок (опционально)
4. Настроить партиционирование таблицы по месяцам (для больших объемов данных)

## Примеры использования API

### Получить список трассировок для плана
```bash
GET /api/traces/?plan_id=<plan_uuid>
```

### Получить все spans трассировки
```bash
GET /api/traces/<trace_id>/spans
```

### Получить статистику
```bash
GET /api/traces/stats/summary?start_time_from=2025-01-01T00:00:00
```

