# Тестирование Prometheus метрик

## Быстрый тест

1. **Установите зависимости** (если еще не установлены):
   ```bash
   pip install prometheus-client==0.19.0
   ```

2. **Запустите сервер**:
   ```bash
   python main.py
   ```

3. **Проверьте endpoint метрик**:
   - Откройте в браузере: http://localhost:8000/metrics
   - Или используйте curl:
     ```bash
     curl http://localhost:8000/metrics
     ```

4. **Используйте тестовый скрипт**:
   ```bash
   python test_metrics.py
   ```

## Что должно быть видно

После запуска сервера и нескольких запросов, в `/metrics` должны быть видны:

- `http_requests_total` - счетчик HTTP запросов
- `http_request_duration_seconds` - гистограмма длительности запросов
- `app_info` - информация о приложении
- После LLM запросов:
  - `llm_requests_total` - счетчик LLM запросов
  - `llm_request_duration_seconds` - длительность LLM запросов
  - `llm_tokens_total` - количество токенов (если доступно)

## Пример вывода

```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{endpoint="/health",method="GET",status_code="200"} 5.0

# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{endpoint="/health",method="GET",status_code="200",le="0.005"} 3.0
http_request_duration_seconds_bucket{endpoint="/health",method="GET",status_code="200",le="0.01"} 5.0
...

# HELP app_info Application information
# TYPE app_info info
app_info{app_env="development",app_name="AARD",version="0.1.0"} 1.0
```

