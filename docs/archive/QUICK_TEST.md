# Быстрое тестирование API

## Шаг 1: Запустите сервер

В терминале:
```bash
cd backend
python main.py
```

Сервер должен запуститься на `http://localhost:8000`

## Шаг 2: Проверьте, что сервер работает

В другом терминале:
```bash
cd C:\work\AARD
python backend/check_server.py
```

Или через браузер:
```
http://localhost:8000/health
```

## Шаг 3: Протестируйте API

### Вариант A: Автоматический тест
```bash
python backend/test_api.py
```

### Вариант B: Ручное тестирование

#### 1. Создать простой инструмент
```bash
curl -X POST http://localhost:8000/api/artifacts/ ^
  -H "Content-Type: application/json" ^
  -d "{\"description\": \"Create a tool to add two numbers\", \"artifact_type\": \"tool\"}"
```

#### 2. Проверить очередь утверждений
```bash
curl http://localhost:8000/api/approvals/
```

#### 3. Создать промпт
```bash
curl -X POST http://localhost:8000/api/prompts/ ^
  -H "Content-Type: application/json" ^
  -d "{\"name\": \"test\", \"prompt_text\": \"You are helpful\", \"prompt_type\": \"system\", \"level\": 1}"
```

## Что проверить:

✅ Миграция применена - таблицы созданы
✅ Сервер запускается без ошибок
✅ API endpoints отвечают (не 404)
✅ Создание артефакта работает (может занять время)
✅ Автоматически создается запрос на утверждение

## Если что-то не работает:

1. Проверьте `.env` файл - все переменные должны быть заполнены
2. Проверьте подключение к БД - `psql -h 10.39.0.101 -U postgres -d aard`
3. Проверьте логи сервера на ошибки
4. Убедитесь, что Ollama серверы доступны

