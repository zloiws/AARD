# Testing Guide

## Обзор

Система тестирования AARD включает unit-тесты и integration-тесты. Тесты организованы в две категории:

- **Unit тесты** (`backend/tests/test_*.py`) - быстрые, изолированные тесты, не требующие внешних зависимостей
- **Integration тесты** (`backend/tests/integration/test_*.py`) - тесты, проверяющие взаимодействие компонентов

## Структура тестов

### Unit тесты

Unit тесты не требуют запущенный сервер и используют моки для внешних зависимостей:

- `test_agent_selection.py` - тесты выбора агента
- `test_plan_execution.py` - тесты выполнения планов
- `test_plan_tree_service.py` - тесты построения дерева планов
- `test_plan_tree_api.py` - тесты API дерева планов (использует TestClient)
- `test_replan_config.py` - тесты конфигурации перепланирования
- `test_auto_replan_service.py` - тесты автоматического перепланирования
- `test_execution_error_detection.py` - тесты обнаружения ошибок

### Integration тесты

Integration тесты могут требовать:
- База данных (используют тестовую БД)
- Запущенный сервер (помечены комментариями)
- Ollama инстансы (опционально)

**Тесты, требующие запущенный сервер:**

Эти тесты делают реальные HTTP запросы к серверу и требуют, чтобы сервер был запущен:

- `test_logging_api.py` - использует `requests.get/post` к `BASE_URL`
- `test_planning_api.py` - использует `requests.get/post` к `BASE_URL`
- `test_planning_api_simple.py` - использует `requests.get` к `BASE_URL`
- `test_chat_api.py` - использует `requests.post` к `BASE_URL`
- `test_chat_with_model.py` - использует `requests.post` к `BASE_URL`
- `test_app.py` - использует `requests.get` к `BASE_URL`
- `test_web_interface.py` - использует `requests.get` к `BASE_URL`
- `test_new_features.py` - использует `requests.get/post` к `BASE_URL`
- `test_logging_system.py` - использует `requests.get/post/put` к `base_url`

**Тесты, НЕ требующие запущенный сервер (используют TestClient):**

FastAPI TestClient создает in-memory приложение и не требует запущенный сервер:

- `test_checkpoint_api_integration.py` - использует `TestClient`
- `test_planning_system_complete.py` - использует `TestClient`
- `test_plan_visualization.py` - использует `TestClient`
- `test_plan_tree_api.py` - использует `TestClient`

**Тесты, использующие async httpx (могут требовать сервер):**

- `test_new_components.py` - использует `httpx.AsyncClient`
- `test_tracing.py` - использует `httpx.AsyncClient`
- `test_api.py` - использует `httpx.AsyncClient`
- `test_prompt_create.py` - использует `httpx.AsyncClient`
- `test_ollama_connection.py` - использует `httpx.AsyncClient`
- `test_model_generation.py` - использует `httpx.AsyncClient`

## Запуск тестов

### Запуск всех unit-тестов

```bash
cd backend
pytest tests/test_*.py -v
```

### Запуск всех integration-тестов

```bash
cd backend
pytest tests/integration/ -v
```

### Запуск тестов без сервера (быстрые тесты)

```bash
cd backend
# Только unit тесты и тесты с TestClient
pytest tests/test_*.py tests/integration/test_checkpoint_api_integration.py tests/integration/test_planning_system_complete.py tests/integration/test_plan_visualization.py tests/test_plan_tree_api.py -v
```

### Запуск тестов с сервером

Сначала запустите сервер:

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Затем в другом терминале:

```bash
cd backend
pytest tests/integration/test_logging_api.py tests/integration/test_planning_api.py -v
```

## Моки и зависимости

### База данных

Unit тесты используют моки для базы данных:

```python
@pytest.fixture
def mock_db(self):
    """Mock database session"""
    return Mock()
```

### HTTP запросы

Для unit тестов используйте моки вместо реальных HTTP запросов:

```python
from unittest.mock import patch, Mock

@patch('httpx.AsyncClient')
async def test_something(mock_client):
    mock_response = Mock()
    mock_response.json.return_value = {"status": "ok"}
    mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
    # ... тест
```

### Ollama клиент

Для тестов, которые используют Ollama клиент, создайте моки:

```python
from unittest.mock import Mock, AsyncMock

mock_ollama_client = Mock()
mock_ollama_client.generate = AsyncMock(return_value={"response": "test"})
```

## Покрытие тестами

Для проверки покрытия:

```bash
cd backend
pytest --cov=app --cov-report=html
```

Отчет будет в `htmlcov/index.html`.

## Best Practices

1. **Unit тесты должны быть быстрыми** - не более секунды на тест
2. **Используйте моки для внешних зависимостей** - БД, HTTP, файловая система
3. **Integration тесты должны быть изолированы** - каждая тестовая сессия создает свою БД
4. **Помечайте тесты, требующие сервер** - используйте комментарии или pytest markers
5. **Используйте fixtures для общих настроек** - БД, клиенты, конфигурация

## Известные проблемы

### Использование plan.status.value

Статус плана хранится как строка, не enum. Используйте `plan.status` вместо `plan.status.value`.

**Исправлено:** Все использования `plan.status.value` заменены на `plan.status`.

### Тесты, требующие сервер

Некоторые integration тесты делают реальные HTTP запросы. Для CI/CD они должны либо:
1. Использовать TestClient вместо реальных запросов
2. Запускать сервер в Docker контейнере
3. Помечаться как `@pytest.mark.skipif` если сервер недоступен

## Будущие улучшения

- [ ] Добавить pytest markers для тестов, требующих сервер
- [ ] Создать Docker compose для запуска тестов с сервером
- [ ] Перевести тесты с реальными HTTP запросами на TestClient где возможно
- [ ] Увеличить покрытие unit-тестами
- [ ] Добавить тесты производительности

