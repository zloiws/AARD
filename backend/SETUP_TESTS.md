# Настройка и запуск интеграционных тестов

## Быстрая установка

```powershell
# 1. Перейдите в директорию backend
cd backend

# 2. Установите зависимости
python -m pip install -r requirements.txt

# 3. Проверьте установку
python -m pytest --version
```

## Запуск тестов

### Простой способ (используя скрипт)
```powershell
cd backend
.\tests\run_integration_tests.ps1
```

### Ручной запуск

```powershell
cd backend

# Самый простой тест (проверка базовой функциональности)
python -m pytest tests/test_integration_simple_question.py::test_simple_question_basic -v -s

# Все простые тесты (~1 минута)
python -m pytest tests/test_integration_simple_question.py -v -s

# Тесты генерации кода (~3-5 минут)
python -m pytest tests/test_integration_code_generation.py -v -s

# Сложные тесты (~10-15 минут)
python -m pytest tests/test_integration_complex_task.py -v -s -m slow
```

## Требования

1. **Python 3.8+** установлен и доступен
2. **Ollama сервер** запущен на `http://localhost:11434`
3. **PostgreSQL** база данных настроена и доступна
4. **Зависимости** установлены из `backend/requirements.txt`

## Проверка окружения

```powershell
# Проверка Python
python --version

# Проверка pytest
python -m pytest --version

# Проверка Ollama (должен вернуть список моделей)
curl http://localhost:11434/api/tags

# Проверка установленных пакетов
python -m pip list | Select-String -Pattern "pytest|fastapi|sqlalchemy"
```

## Решение проблем

### Проблема: "pytest не найден"
```powershell
cd backend
python -m pip install pytest pytest-asyncio
```

### Проблема: "requirements.txt не найден"
Убедитесь, что вы в директории `backend`, а не в корне проекта:
```powershell
cd backend
ls requirements.txt  # Должен показать файл
```

### Проблема: "Ollama недоступен"
Запустите Ollama сервер перед запуском тестов:
```powershell
# Проверка
curl http://localhost:11434/api/tags
```

### Проблема: "База данных недоступна"
Проверьте настройки в `.env` файле в директории `backend`:
- `DATABASE_URL` должен быть правильным
- PostgreSQL должен быть запущен

## Структура файлов

```
AARD/
├── backend/                    ← Работайте здесь!
│   ├── requirements.txt        ← Зависимости здесь
│   ├── tests/
│   │   ├── test_integration_*.py
│   │   ├── run_integration_tests.ps1
│   │   └── QUICK_START.md
│   └── .env                    ← Настройки БД здесь
└── ...
```

## Следующие шаги

После успешной установки зависимостей:

1. Запустите простой тест для проверки:
   ```powershell
   cd backend
   python -m pytest tests/test_integration_simple_question.py::test_simple_question_basic -v -s
   ```

2. Если тест прошел успешно, запустите все простые тесты:
   ```powershell
   python -m pytest tests/test_integration_simple_question.py -v -s
   ```

3. Затем переходите к более сложным тестам по мере необходимости.
