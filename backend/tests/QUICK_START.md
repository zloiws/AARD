# Быстрый старт интеграционных тестов

## Windows PowerShell

### Шаг 1: Установка зависимостей

```powershell
# Перейдите в директорию backend
cd backend

# Установите зависимости
python -m pip install -r requirements.txt
```

### Шаг 2: Проверка окружения

```powershell
# Проверьте Python
python --version

# Проверьте pytest
python -m pytest --version

# Проверьте Ollama (должен быть запущен)
curl http://localhost:11434/api/tags
```

### Вариант 1: Использовать скрипт
```powershell
cd backend
.\tests\run_integration_tests.ps1
```

### Вариант 2: Запустить вручную

```powershell
cd backend

# Простой тест (быстрый)
python -m pytest tests/test_integration_simple_question.py -v -s

# Все простые тесты
python -m pytest tests/test_integration_simple_question.py -v -s

# Тесты генерации кода
python -m pytest tests/test_integration_code_generation.py -v -s

# Сложные тесты (медленные)
python -m pytest tests/test_integration_complex_task.py -v -s -m slow
```

## Важно!

1. **Всегда используйте `python -m pytest`** вместо просто `pytest` - это гарантирует использование правильной версии pytest из вашего окружения.

2. **Убедитесь, что вы в директории `backend`** перед запуском команд.

3. **requirements.txt находится в `backend/requirements.txt`**, не в корне проекта.

## Проверка перед запуском

1. **Ollama должен быть запущен**:
   ```powershell
   curl http://localhost:11434/api/tags
   ```

2. **База данных должна быть доступна** (проверьте настройки в `.env`)

3. **Установлены зависимости**:
   ```powershell
   cd backend
   python -m pip install -r requirements.txt
   ```

## Если тесты не запускаются

1. Убедитесь, что вы в директории `backend`
2. Используйте `python -m pytest` вместо `pytest`
3. Проверьте, что все зависимости установлены из `backend/requirements.txt`
4. Проверьте доступность Ollama сервера
5. Проверьте настройки базы данных в `.env`

## Структура проекта

```
AARD/
├── backend/
│   ├── requirements.txt  ← Здесь находятся зависимости
│   ├── tests/
│   │   ├── test_integration_*.py
│   │   └── run_integration_tests.ps1
│   └── ...
└── ...
```
