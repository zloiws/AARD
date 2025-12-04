# Исправление OpenTelemetry

## Проблема

OpenTelemetry был обязательной зависимостью, что вызывало проблемы:
1. Ошибки импорта, если пакеты не установлены
2. Устаревшие версии (0.42b0 - beta версии)
3. Невозможность запустить приложение без OpenTelemetry

## Решение

### 1. Обновлены версии в requirements.txt

Обновлены до более свежих версий:
- `opentelemetry-api==1.24.0` (было 1.21.0)
- `opentelemetry-sdk==1.24.0` (было 1.21.0)
- `opentelemetry-instrumentation-*==0.45b0` (было 0.42b0)
- `opentelemetry-exporter-otlp-proto-http==1.24.0` (было 1.21.0)

### 2. Сделано опциональным

OpenTelemetry теперь опциональная зависимость:
- Если пакеты не установлены - приложение работает без трассировки
- Выводится предупреждение с инструкцией по установке
- Все функции трассировки имеют заглушки (NoOp)

### 3. Изменения в коде

**`backend/app/core/tracing.py`:**
- Добавлена проверка `OPENTELEMETRY_AVAILABLE`
- Все импорты обернуты в `try/except`
- Функции работают даже без OpenTelemetry:
  - `get_tracer()` - возвращает NoOpTracer
  - `get_current_trace_id()` - возвращает None
  - `get_current_span_id()` - возвращает None
  - `add_span_attributes()` - ничего не делает
  - `configure_tracing()` - выводит предупреждение и выходит
  - `shutdown_tracing()` - проверяет доступность перед вызовом

## Использование

### Вариант 1: Без OpenTelemetry (по умолчанию)

Приложение работает без установки OpenTelemetry:
- Трассировка отключена
- Все функции трассировки - заглушки
- В логах будет предупреждение при попытке включить трассировку

### Вариант 2: С OpenTelemetry

1. Установить пакеты:
```bash
pip install opentelemetry-api==1.24.0 \
            opentelemetry-sdk==1.24.0 \
            opentelemetry-instrumentation-fastapi==0.45b0 \
            opentelemetry-instrumentation-sqlalchemy==0.45b0 \
            opentelemetry-instrumentation-httpx==0.45b0 \
            opentelemetry-instrumentation-aiohttp-client==0.45b0 \
            opentelemetry-exporter-otlp-proto-http==1.24.0
```

2. Включить в `.env`:
```env
ENABLE_TRACING=true
TRACING_EXPORTER=database  # или console, otlp
```

## Проверка

```bash
# Проверка импорта без OpenTelemetry
python -c "from app.core.tracing import configure_tracing, get_tracer; print('OK')"

# Проверка с OpenTelemetry
pip install opentelemetry-api opentelemetry-sdk
python -c "from app.core.tracing import configure_tracing; print('OK')"
```

## Преимущества

1. ✅ Приложение запускается без OpenTelemetry
2. ✅ Нет ошибок импорта
3. ✅ Обновленные версии пакетов
4. ✅ Легко включить/выключить через конфигурацию
5. ✅ Понятные сообщения об ошибках

## Рекомендации

- Для разработки: можно работать без OpenTelemetry
- Для production: установить OpenTelemetry для мониторинга
- Для отладки: использовать `console` exporter
- Для production: использовать `database` или `otlp` exporter

