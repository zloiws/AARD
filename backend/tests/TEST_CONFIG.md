# Конфигурация тестов

## Используемая модель

Все интеграционные тесты используют конкретную модель из базы данных:

- **Сервер:** 10.39.0.6 (ищется по URL/IP)
- **Модель:** gemma3:4b

## Как изменить модель для тестов

Если нужно использовать другую модель, измените константы в функции `get_test_model_and_server()`:

```python
def get_test_model_and_server(db: Session):
    target_server_url = "10.39.0.6"  # IP или URL сервера
    target_model_name = "gemma3:4b"  # Имя модели
    # ...
```

Эта функция используется во всех тестах:
- `test_integration_basic.py`
- `test_integration_simple_question.py`
- `test_integration_code_generation.py`

## Запуск тестов

```powershell
cd backend

# Базовый тест
python -m pytest tests/test_integration_basic.py -v -s

# Простые тесты
python -m pytest tests/test_integration_simple_question.py -v -s

# Все тесты
python -m pytest tests/test_integration_*.py -v -s
```

## Требования

1. Сервер с IP 10.39.0.6 должен быть в БД и активен
2. Модель gemma3:4b должна быть на этом сервере и активна
3. Ollama сервер должен быть доступен по указанному адресу
