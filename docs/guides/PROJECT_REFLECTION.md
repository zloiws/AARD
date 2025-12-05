# Система саморефлексии проекта

## Обзор

Система саморефлексии проекта (Phase 3) предназначена для автоматического сбора, анализа и визуализации метрик на уровне всего проекта. Она позволяет отслеживать производительность системы, успешность выполнения задач, тренды во времени и генерировать автоматические рекомендации по улучшению.

## Архитектура

Система состоит из трех основных этапов:

1. **Этап 3.1: Система метрик проекта** - сбор и хранение метрик
2. **Этап 3.2: Регулярный самоаудит** - автоматический анализ и рекомендации
3. **Этап 3.3: Dashboard метрик проекта** - визуализация и отчеты

## Этап 3.1: Система метрик проекта

### Модель ProjectMetric

Модель `ProjectMetric` (`backend/app/models/project_metric.py`) хранит агрегированные метрики проекта.

**Поля:**

- `id` (UUID): Уникальный идентификатор метрики
- `metric_type` (Enum `MetricType`): Тип метрики (PERFORMANCE, TASK_SUCCESS, EXECUTION_TIME, TASK_DISTRIBUTION, TREND, AGGREGATE)
- `metric_name` (String): Имя метрики (например, "task_success_rate", "avg_execution_time")
- `period` (Enum `MetricPeriod`): Период агрегации (HOUR, DAY, WEEK, MONTH)
- `period_start` (DateTime): Начало периода
- `period_end` (DateTime): Конец периода
- `value` (Float): Основное значение метрики
- `count` (Integer): Количество образцов
- `min_value` (Float): Минимальное значение в периоде
- `max_value` (Float): Максимальное значение в периоде
- `sum_value` (Float): Сумма значений (для расчета средних)
- `metric_metadata` (JSONB): Дополнительные данные метрики
- `created_at` (DateTime): Время создания
- `updated_at` (DateTime): Время последнего обновления

**Пример использования:**

```python
from app.models.project_metric import ProjectMetric, MetricType, MetricPeriod
from datetime import datetime, timedelta

period_start = datetime.utcnow() - timedelta(hours=1)
period_end = datetime.utcnow()

metric = ProjectMetric(
    metric_type=MetricType.PERFORMANCE,
    metric_name="task_success_rate",
    period=MetricPeriod.HOUR,
    period_start=period_start,
    period_end=period_end,
    value=0.85,
    count=100
)
```

### ProjectMetricsService

Сервис `ProjectMetricsService` (`backend/app/services/project_metrics_service.py`) предоставляет методы для работы с метриками проекта.

**Основные методы:**

- `record_metric()`: Записать метрику в базу данных
- `collect_performance_metrics()`: Собрать метрики производительности за период
- `collect_task_distribution()`: Собрать метрики распределения задач
- `get_overview()`: Получить обзор метрик за период
- `get_trends()`: Получить тренды метрики во времени
- `compare_periods()`: Сравнить метрики между двумя периодами

**Пример использования:**

```python
from app.services.project_metrics_service import ProjectMetricsService
from app.core.database import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()
service = ProjectMetricsService(db)

# Получить обзор за последние 30 дней
overview = service.get_overview(days=30)

# Получить тренды успешности задач
trends = service.get_trends(
    metric_name="task_success_rate",
    days=7,
    period=MetricPeriod.DAY
)

# Сравнить два периода
period1_start = datetime.utcnow() - timedelta(days=14)
period1_end = datetime.utcnow() - timedelta(days=7)
period2_start = datetime.utcnow() - timedelta(days=7)
period2_end = datetime.utcnow()

comparison = service.compare_periods(
    period1_start, period1_end,
    period2_start, period2_end
)
```

### Типы метрик

1. **PERFORMANCE**: Общая производительность системы
   - `task_success_rate`: Процент успешных задач
   - `avg_execution_time`: Среднее время выполнения

2. **TASK_SUCCESS**: Метрики успешности задач
   - Распределение по статусам
   - Процент успешных/проваленных задач

3. **EXECUTION_TIME**: Метрики времени выполнения
   - Среднее время выполнения
   - Минимальное/максимальное время
   - Распределение по времени

4. **TASK_DISTRIBUTION**: Распределение задач
   - По статусам
   - По приоритетам
   - По уровням автономии

5. **TREND**: Тренды во времени
   - Изменение метрик во времени
   - Прогнозирование

6. **AGGREGATE**: Агрегированные метрики
   - Сводные показатели
   - Комплексные метрики

## Миграции

Для создания таблицы `project_metrics` используется Alembic миграция: `backend/alembic/versions/022_add_project_metrics.py`.

## Тестирование

- **Unit тесты**: `backend/tests/test_project_metrics_service.py`
  - Тесты записи метрик
  - Тесты сбора метрик производительности
  - Тесты сбора распределения задач
  - Тесты получения обзора
  - Тесты получения трендов
  - Тесты сравнения периодов

## Этап 3.1.2: Сбор метрик в реальном времени

### Интеграция с сервисами

Метрики проекта автоматически собираются в следующих сервисах:

#### PlanningService

Метрики собираются при:
- **Анализе задачи** (`_analyze_task`): время анализа задачи
- **Декомпозиции задачи** (`_decompose_task`): время декомпозиции и количество шагов

**Собираемые метрики:**
- `task_analysis_time`: время анализа задачи (секунды)
- `task_decomposition_time`: время декомпозиции задачи (секунды)

#### ExecutionService

Метрики собираются при:
- **Выполнении шага** (`execute_step`): время выполнения каждого шага
- **Выполнении плана** (`execute_plan`): общее время выполнения и успешность

**Собираемые метрики:**
- `step_execution_time`: время выполнения шага (секунды)
- `plan_execution_time`: время выполнения плана (секунды)
- `plan_execution_success`: успешность выполнения плана (1.0 = успех, 0.0 = провал)

#### PromptService

Метрики собираются при:
- **Использовании промпта** (`record_usage`): время выполнения
- **Успешном использовании** (`record_success`): успешность промпта
- **Неудачном использовании** (`record_failure`): успешность промпта

**Собираемые метрики:**
- `prompt_execution_time`: время выполнения промпта (секунды)
- `prompt_success_rate`: процент успешных использований промпта

### Агрегация метрик

Метрики автоматически агрегируются по периодам:
- **HOUR**: Агрегация по часам
- **DAY**: Агрегация по дням
- **WEEK**: Агрегация по неделям
- **MONTH**: Агрегация по месяцам

Периоды округляются до границ (например, час начинается с :00:00), что обеспечивает консистентную агрегацию.

### Примеры использования

```python
from app.services.project_metrics_service import ProjectMetricsService
from app.core.database import SessionLocal
from datetime import datetime, timedelta

db = SessionLocal()
service = ProjectMetricsService(db)

# Метрики автоматически собираются при работе сервисов
# Например, при использовании PlanningService:
from app.services.planning_service import PlanningService

planning_service = PlanningService(db)
# При вызове create_plan метрики автоматически записываются

# Получить собранные метрики
overview = service.get_overview(days=7)
print(f"Success rate: {overview['performance']['success_rate']}")
print(f"Avg execution time: {overview['performance']['avg_execution_time']}")
```

## Этап 3.1.3: API для метрик проекта

### Endpoints

#### GET /api/metrics/project/overview

Получить обзор метрик проекта за указанный период.

**Параметры:**
- `days` (int, default=30): Количество дней для анализа (1-365)

**Ответ:**
```json
{
  "period": {
    "days": 30,
    "start": "2025-11-05T00:00:00Z",
    "end": "2025-12-05T00:00:00Z"
  },
  "performance": {
    "success_rate": 0.85,
    "avg_execution_time": 2.5,
    "total_tasks": 100
  },
  "distribution": {
    "by_status": {...},
    "by_type": {...}
  },
  "plans": {
    "total": 50,
    "completed": 45,
    "failed": 5
  },
  "recent_metrics": [...]
}
```

#### GET /api/metrics/project/trends

Получить тренды для конкретной метрики.

**Параметры:**
- `metric_name` (str, required): Имя метрики
- `metric_type` (str, optional): Тип метрики (performance, task_success, execution_time, etc.)
- `days` (int, default=30): Количество дней для анализа (1-365)
- `period` (str, default="day"): Период агрегации (hour, day, week, month)

**Ответ:**
```json
{
  "metric_name": "task_success_rate",
  "metric_type": "task_success",
  "period": "day",
  "days": 30,
  "data_points": [
    {
      "period_start": "2025-12-01T00:00:00Z",
      "period_end": "2025-12-02T00:00:00Z",
      "value": 0.85,
      "count": 10
    },
    ...
  ]
}
```

#### GET /api/metrics/project/comparison

Сравнить метрики между двумя периодами.

**Параметры:**
- `period1_start` (str, required): Начало первого периода (ISO format)
- `period1_end` (str, required): Конец первого периода (ISO format)
- `period2_start` (str, required): Начало второго периода (ISO format)
- `period2_end` (str, required): Конец второго периода (ISO format)

**Ответ:**
```json
{
  "period1": {
    "start": "2025-11-01T00:00:00Z",
    "end": "2025-11-15T00:00:00Z",
    "metrics": {...}
  },
  "period2": {
    "start": "2025-11-16T00:00:00Z",
    "end": "2025-11-30T00:00:00Z",
    "metrics": {...}
  },
  "changes": {
    "success_rate": {
      "period1": 0.80,
      "period2": 0.85,
      "change": 0.05,
      "change_percent": 6.25
    },
    ...
  }
}
```

#### GET /api/metrics/project/metrics

Список метрик с фильтрацией и пагинацией.

**Параметры:**
- `metric_type` (str, optional): Фильтр по типу метрики
- `metric_name` (str, optional): Фильтр по имени метрики
- `period` (str, optional): Фильтр по периоду агрегации
- `limit` (int, default=100): Максимальное количество результатов (1-1000)
- `offset` (int, default=0): Смещение для пагинации

**Ответ:**
```json
[
  {
    "id": "uuid",
    "metric_type": "performance",
    "metric_name": "task_success_rate",
    "period": "hour",
    "period_start": "2025-12-05T12:00:00Z",
    "period_end": "2025-12-05T13:00:00Z",
    "value": 0.85,
    "count": 10,
    "min_value": 0.70,
    "max_value": 0.95,
    "sum_value": 8.5,
    "metadata": {...},
    "created_at": "2025-12-05T13:00:00Z",
    "updated_at": "2025-12-05T13:00:00Z"
  },
  ...
]
```

### Примеры использования

```bash
# Получить обзор за последние 7 дней
curl "http://localhost:8000/api/metrics/project/overview?days=7"

# Получить тренды успешности задач за месяц
curl "http://localhost:8000/api/metrics/project/trends?metric_name=task_success_rate&days=30&period=day"

# Сравнить два периода
curl "http://localhost:8000/api/metrics/project/comparison?period1_start=2025-11-01T00:00:00Z&period1_end=2025-11-15T00:00:00Z&period2_start=2025-11-16T00:00:00Z&period2_end=2025-11-30T00:00:00Z"

# Список метрик производительности
curl "http://localhost:8000/api/metrics/project/metrics?metric_type=performance&limit=50"
```

## Этап 3.2: Регулярный самоаудит

### SelfAuditService

Сервис для автоматического самоанализа проекта на всех уровнях.

#### Методы аудита

**audit_performance()** - Анализ производительности системы
- Анализ успешности выполнения задач
- Анализ времени выполнения планов
- Выявление проблем производительности
- Рекомендации по оптимизации

**audit_quality()** - Анализ качества планов
- Анализ успешности выполнения планов
- Анализ сложности планов (количество шагов)
- Анализ точности оценки длительности
- Рекомендации по улучшению качества планирования

**audit_prompts()** - Анализ эффективности промптов
- Анализ использования промптов
- Анализ успешности промптов
- Выявление неэффективных промптов
- Рекомендации по улучшению промптов

**audit_errors()** - Анализ ошибок и паттернов
- Классификация ошибок
- Выявление паттернов ошибок
- Анализ причин провалов планов
- Рекомендации по исправлению

**generate_report()** - Генерация полного отчета
- Выполнение всех типов аудита
- Анализ трендов
- Генерация сводки (текстовой или через LLM)
- Сохранение отчета в БД

### Модель AuditReport

Модель для хранения отчетов аудита:

- `audit_type`: Тип аудита (PERFORMANCE, QUALITY, PROMPTS, ERRORS, FULL)
- `status`: Статус аудита (PENDING, IN_PROGRESS, COMPLETED, FAILED)
- `period_start/period_end`: Период аудита
- `summary`: Текстовая сводка
- `findings`: Детальные находки
- `recommendations`: Рекомендации по улучшению
- `metrics`: Проанализированные метрики
- `trends`: Анализ трендов

### Примеры использования

```python
from app.services.self_audit_service import SelfAuditService
from app.models.audit_report import AuditType
from datetime import datetime, timedelta

service = SelfAuditService(db)

# Выполнить аудит производительности
period_start = datetime.utcnow() - timedelta(days=7)
period_end = datetime.utcnow()

performance_result = await service.audit_performance(period_start, period_end)
print(f"Success rate: {performance_result['metrics']['success_rate']}")

# Сгенерировать полный отчет
report = await service.generate_report(
    audit_type=AuditType.FULL,
    period_start=period_start,
    period_end=period_end,
    use_llm=True  # Использовать LLM для генерации сводки
)

print(f"Report ID: {report.id}")
print(f"Summary: {report.summary}")
print(f"Findings: {len(report.findings.get('all_findings', []))}")
```

## Дальнейшее развитие

- **Этап 3.2.2**: Планировщик регулярных аудитов
- **Этап 3.2.3**: Анализ трендов и рекомендации
- **Этап 3.3**: Dashboard для визуализации метрик

