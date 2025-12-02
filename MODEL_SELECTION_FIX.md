# Исправление логики выбора моделей

## Проблема

Выбиралась модель с одного сервера, но отвечала модель с другого сервера.

**Пример:**
- Выбрано: Сервер `10.39.0.6`, Модель `gemma3:4b`
- Отвечает: Модель `huihui_ai/deepseek-r1-abliterated:8b` (с сервера 10.39.0.101)

## Причина

1. **Fallback логика** заменяла выбранный instance другим, если health check проваливался
2. **Неправильная нормализация URL** - сравнение не работало корректно
3. **Сложная вложенная логика** - было сложно отследить, какой instance выбран

## Решение

### 1. Переписан алгоритм выбора instance с приоритетами:

**ПРИОРИТЕТ 1: Если указан `server_url`**
- Всегда использовать указанный сервер
- Найти instance в конфигурации по URL
- Если не найден - создать динамический instance
- **ВАЖНО:** НЕ делать fallback на другие instances, даже если health check провалился

**ПРИОРИТЕТ 2: Если указан `model` (но нет server_url)**
- Искать instance по точному имени модели
- Если не найден - искать по базовому имени (без тега)
- Если не найден - использовать первый доступный instance с запрошенной моделью

**ПРИОРИТЕТ 3: Автовыбор по `task_type`**
- Использовать логику выбора по типу задачи
- Fallback на первый доступный instance

### 2. Добавлена нормализация URL:

```python
def _normalize_server_url(self, url: str) -> str:
    """Normalize server URL to standard format"""
    url = url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"http://{url}"
    if not url.endswith("/v1"):
        if url.endswith("/v1/"):
            url = url.rstrip("/")
        else:
            url = url.rstrip("/") + "/v1"
    return url
```

### 3. Отдельные методы для работы с instances:

- `_normalize_server_url()` - нормализация URL
- `_create_dynamic_instance()` - создание динамического instance
- `_find_instance_by_url()` - поиск instance по URL

### 4. Отключен fallback для явно указанных серверов:

```python
# Если server_url явно указан, НЕ делать fallback
if not is_dynamic_instance:
    if not await self.health_check(instance):
        if not server_url:
            # Fallback только если server_url НЕ указан
            ...
        else:
            # Если server_url указан - выбросить ошибку, но НЕ делать fallback
            raise OllamaError(f"Ollama instance {instance.url} is not available")
```

## Результат

Теперь:
- ✅ Если выбран сервер `10.39.0.6` и модель `gemma3:4b` - запрос идет на `10.39.0.6` с моделью `gemma3:4b`
- ✅ Если выбран сервер `10.39.0.101` и модель `qwen3-vl:8b` - запрос идет на `10.39.0.101` с моделью `qwen3-vl:8b`
- ✅ Нет fallback на другой сервер, если указан конкретный server_url
- ✅ Правильная нормализация URL для сравнения
- ✅ Поддержка динамических серверов (не в конфигурации)

## Проверка

После исправлений запросы должны идти на правильный сервер с правильной моделью.

