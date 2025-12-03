# Prometheus Metrics

## Обзор

AARD интегрирован с Prometheus для сбора метрик производительности и мониторинга системы.

## Установка

Метрики уже включены в проект. Убедитесь, что установлен `prometheus-client`:

```bash
pip install prometheus-client==0.19.0
```

## Endpoint

Метрики доступны по адресу:

```
GET /metrics
```

Возвращает метрики в формате Prometheus text format.

## Доступные метрики

### HTTP метрики

- `http_requests_total` - Общее количество HTTP запросов
  - Labels: `method`, `endpoint`, `status_code`
- `http_request_duration_seconds` - Длительность HTTP запросов
  - Labels: `method`, `endpoint`, `status_code`
- `http_errors_total` - Количество HTTP ошибок
  - Labels: `method`, `endpoint`, `status_code`, `error_type`

### LLM метрики

- `llm_requests_total` - Общее количество LLM запросов
  - Labels: `model`, `server_url`, `task_type`, `status`
- `llm_request_duration_seconds` - Длительность LLM запросов
  - Labels: `model`, `server_url`, `task_type`
- `llm_tokens_total` - Общее количество токенов
  - Labels: `model`, `type` (input/output)
- `llm_errors_total` - Количество ошибок LLM
  - Labels: `model`, `server_url`, `error_type`
- `llm_model_loaded` - Статус загрузки модели (1 = загружена, 0 = не загружена)
  - Labels: `model`, `server_url`

### Метрики выполнения планов

- `plan_executions_total` - Общее количество выполнений планов
  - Labels: `status` (success/failed/cancelled)
- `plan_execution_duration_seconds` - Длительность выполнения планов
  - Labels: `status`
- `plan_steps_total` - Общее количество шагов планов
  - Labels: `step_type` (action/decision/validation), `status`
- `plan_step_duration_seconds` - Длительность выполнения шагов
  - Labels: `step_type`

### Метрики очередей

- `queue_tasks_total` - Общее количество задач в очередях
  - Labels: `queue_name`, `priority`
- `queue_tasks_processed_total` - Количество обработанных задач
  - Labels: `queue_name`, `status` (success/failed/retried)
- `queue_task_duration_seconds` - Длительность обработки задач
  - Labels: `queue_name`
- `queue_size` - Текущий размер очереди
  - Labels: `queue_name`, `status` (pending/processing/failed)
- `queue_retries_total` - Количество повторных попыток
  - Labels: `queue_name`

### Метрики БД

- `db_queries_total` - Общее количество запросов к БД
  - Labels: `operation` (select/insert/update/delete), `table`
- `db_query_duration_seconds` - Длительность запросов к БД
  - Labels: `operation`, `table`
- `db_errors_total` - Количество ошибок БД
  - Labels: `operation`, `error_type`
- `db_connection_pool_size` - Размер пула соединений
  - Labels: `state` (active/idle/overflow)

### Метрики утверждений

- `approval_requests_total` - Общее количество запросов на утверждение
  - Labels: `request_type`, `status` (pending/approved/rejected)
- `approval_request_duration_seconds` - Время от запроса до решения
  - Labels: `request_type`, `status`

### Метрики артефактов

- `artifacts_total` - Общее количество созданных артефактов
  - Labels: `artifact_type`, `status` (draft/approved/active)
- `artifact_generation_duration_seconds` - Длительность генерации артефактов
  - Labels: `artifact_type`

### Системная информация

- `app_info` - Информация о приложении
  - Labels: `app_name`, `app_env`, `version`

## Тестирование

### 1. Запустите сервер

```bash
cd backend
python main.py
```

### 2. Проверьте endpoint метрик

```bash
curl http://localhost:8000/metrics
```

Или откройте в браузере: http://localhost:8000/metrics

### 3. Используйте тестовый скрипт

```bash
cd backend
python test_metrics.py
```

## Настройка Prometheus

### prometheus.yml

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'aard'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Запуск Prometheus

```bash
prometheus --config.file=prometheus.yml
```

## Grafana Dashboard

Импортируйте метрики в Grafana для визуализации:

1. Добавьте Prometheus как источник данных
2. Создайте дашборды для:
   - HTTP запросы (rate, latency, errors)
   - LLM запросы (throughput, latency, tokens)
   - Выполнение планов (success rate, duration)
   - Очереди (size, processing time)
   - БД (query performance)

## Примеры запросов PromQL

### Rate HTTP запросов

```promql
rate(http_requests_total[5m])
```

### Средняя длительность LLM запросов

```promql
rate(llm_request_duration_seconds_sum[5m]) / rate(llm_request_duration_seconds_count[5m])
```

### Количество ошибок LLM

```promql
sum(rate(llm_errors_total[5m])) by (error_type)
```

### Размер очереди

```promql
queue_size
```

### Успешность выполнения планов

```promql
sum(rate(plan_executions_total{status="success"}[5m])) / sum(rate(plan_executions_total[5m]))
```

## Алерты

Пример конфигурации алертов в Prometheus:

```yaml
groups:
  - name: aard_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_errors_total[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High HTTP error rate"
      
      - alert: LLMRequestTimeout
        expr: rate(llm_errors_total{error_type="timeout"}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High LLM timeout rate"
      
      - alert: QueueBacklog
        expr: queue_size{status="pending"} > 100
        for: 10m
        annotations:
          summary: "Large queue backlog"
```

## Мультипроцесс режим

Для работы с несколькими процессами (например, с Gunicorn), установите переменную окружения:

```bash
export PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
```

Метрики будут автоматически собираться из всех процессов.

