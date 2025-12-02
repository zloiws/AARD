# Исправление Health Check

## Проблема

Модели показывались как недоступные (✗), хотя Ollama API работал и отвечал на запросы.

## Диагностика

Тесты показали:
1. ✅ Прямое подключение работает - endpoints `/api/tags`, `/api/version` отвечают с кодом 200
2. ✅ Generate endpoint работает - можно генерировать ответы
3. ❌ Health check возвращал False

## Причина

URL в конфигурации содержит `/v1`:
- `http://10.39.0.101:11434/v1`
- `http://10.39.0.6:11434/v1`

Но Ollama API endpoints находятся НЕ под `/v1/api/tags`, а просто `/api/tags`.

Когда health_check делал запрос:
- Base URL: `http://10.39.0.101:11434/v1/`
- Endpoint: `/api/tags`
- Результат: `http://10.39.0.101:11434/v1/api/tags` ❌ (неправильный)

Правильный URL должен быть:
- `http://10.39.0.101:11434/api/tags` ✅

## Решение

Исправлен метод `health_check` и `generate` в `ollama_client.py`:

1. **Health Check**: Убирает `/v1` из URL перед проверкой
2. **Generate**: Убирает `/v1` из URL перед запросом к `/api/generate`
3. **Generate Stream**: То же самое для streaming

### Изменения в коде

```python
# Было:
client = await self._get_client(instance)
response = await client.get("/api/tags", timeout=5.0)

# Стало:
base_url = instance.url
if base_url.endswith("/v1"):
    base_url = base_url[:-3]  # Remove /v1

async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
    response = await client.get("/api/tags", timeout=5.0)
```

## Результат

✅ Health check теперь правильно определяет доступность моделей
✅ Веб-интерфейс показывает статус моделей корректно
✅ Generate endpoint работает правильно

## Тестирование

После исправления:
```
TEST 2: Health Check Method
1. Testing instance: huihui_ai/deepseek-r1-abliterated:8b
   Health check result: ✓ Available

2. Testing instance: qwen3-coder:30b-a3b-q4_K_M
   Health check result: ✓ Available
```

## Примечание

URL с `/v1` в конфигурации оставлен для совместимости с будущими изменениями или если понадобится использовать другой API endpoint. При работе с Ollama API `/v1` нужно удалять из base URL.

