# Система ранжирования запросов - Завершено

## Реализованные компоненты

### 1. Модели данных
- ✅ `RequestLog` - основная таблица для хранения всех запросов
- ✅ `RequestConsequence` - таблица для отслеживания последствий запросов
- ✅ Миграция `006_add_request_logs.py` применена

### 2. Сервис логирования
- ✅ `RequestLogger` - сервис для логирования запросов
- ✅ Алгоритм ранжирования:
  - `success_score` - оценка успешности (0.0-1.0)
  - `importance_score` - оценка важности по типу запроса (0.0-1.0)
  - `impact_score` - оценка влияния на систему (0.0-1.0)
  - `overall_rank` - общий ранг с учетом времени (0.0-1.0)

### 3. Интеграция
- ✅ Интегрировано в `chat.py` - логирование всех чат-запросов
- ✅ Интегрировано в `planning_service.py` - логирование создания планов
- ✅ Автоматическое отслеживание последствий (созданные планы, утверждения)

### 4. API для анализа
- ✅ `GET /api/requests/` - список запросов с фильтрами
- ✅ `GET /api/requests/ranked` - топ запросов по рангу
- ✅ `GET /api/requests/{request_id}` - детали запроса
- ✅ `GET /api/requests/{request_id}/consequences` - последствия запроса
- ✅ `GET /api/requests/stats/summary` - статистика по запросам

## Алгоритм ранжирования

### Веса компонентов:
- `success_score`: 30%
- `importance_score`: 30%
- `impact_score`: 30%
- `recency_score`: 10% (время с момента создания)

### Оценка важности по типу:
- `artifact_generation`: 0.8
- `plan_generation`: 0.7
- `plan_execution`: 0.7
- `approval_request`: 0.6
- `chat`: 0.3
- `code_generation`: 0.8
- `code_analysis`: 0.6

### Оценка влияния:
- Базовая оценка: 0.5
- +0.1 за каждый созданный артефакт/план
- +0.05 за каждое утверждение
- +0.15 за каждый измененный артефакт
- Учитывается impact_score из consequences

## Использование

### Логирование запроса:
```python
from app.services.request_logger import RequestLogger

request_logger = RequestLogger(db)
request_log = request_logger.log_request(
    request_type="chat",
    request_data={"message": "..."},
    status="success",
    model_used="model_name",
    server_url="http://...",
    duration_ms=1234,
    session_id="session_id",
    trace_id="trace_id",
)
```

### Добавление последствия:
```python
request_logger.add_consequence(
    request_id=request_log.id,
    consequence_type="plan_created",
    entity_type="plan",
    entity_id=plan.id,
    impact_type="positive",
    impact_score=0.7,
)
```

## Следующие шаги

1. Интегрировать в `execution_service.py` - логирование выполнения планов
2. Интегрировать в `artifact_generator.py` - логирование создания артефактов
3. Создать веб-интерфейс для просмотра и анализа запросов
4. Добавить автоматическое обновление рангов при изменении последствий

