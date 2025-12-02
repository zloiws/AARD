# Руководство по тестированию API системы эволюции

## Предварительные требования

1. ✅ Миграция БД применена (`alembic upgrade head`)
2. ✅ Сервер запущен (`python backend/main.py`)
3. ✅ .env файл настроен с параметрами подключения

## Запуск тестов

### Вариант 1: Автоматический тест (Python скрипт)

```bash
# В отдельном терминале запустите сервер
cd backend
python main.py

# В другом терминале запустите тесты
cd C:\work\AARD
python backend/test_api.py
```

### Вариант 2: Ручное тестирование через curl/Postman

## 1. Проверка здоровья сервера

```bash
curl http://localhost:8000/health
```

Ожидаемый ответ:
```json
{"status": "healthy"}
```

## 2. Тестирование API утверждений

### Получить список ожидающих утверждения
```bash
curl http://localhost:8000/api/approvals/
```

### Получить конкретный запрос на утверждение
```bash
curl http://localhost:8000/api/approvals/{request_id}
```

## 3. Тестирование API артефактов

### Создать новый инструмент
```bash
curl -X POST http://localhost:8000/api/artifacts/ \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a tool to search files by name and extension",
    "artifact_type": "tool"
  }'
```

**Важно:** Это займет 30-60 секунд, так как использует LLM для генерации кода.

### Получить список артефактов
```bash
curl http://localhost:8000/api/artifacts/
```

### Получить детали артефакта
```bash
curl http://localhost:8000/api/artifacts/{artifact_id}
```

### Создать нового агента
```bash
curl -X POST http://localhost:8000/api/artifacts/ \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create an agent that helps with code review",
    "artifact_type": "agent"
  }'
```

## 4. Тестирование API промптов

### Создать промпт
```bash
curl -X POST http://localhost:8000/api/prompts/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "system_prompt_v1",
    "prompt_text": "You are a helpful AI assistant specialized in code generation.",
    "prompt_type": "system",
    "level": 1
  }'
```

### Получить список промптов
```bash
curl http://localhost:8000/api/prompts/
```

### Обновить промпт
```bash
curl -X PUT http://localhost:8000/api/prompts/{prompt_id} \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_text": "Updated prompt text"
  }'
```

## 5. Полный цикл: Создание → Утверждение → Активация

### Шаг 1: Создать артефакт
```bash
ARTIFACT_RESPONSE=$(curl -X POST http://localhost:8000/api/artifacts/ \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a tool to calculate factorial",
    "artifact_type": "tool"
  }')

echo $ARTIFACT_RESPONSE
# Сохраните artifact_id из ответа
```

### Шаг 2: Проверить очередь утверждений
```bash
curl http://localhost:8000/api/approvals/
# Найдите request_id для созданного артефакта
```

### Шаг 3: Утвердить запрос
```bash
curl -X POST http://localhost:8000/api/approvals/{request_id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "feedback": "Looks good, approved!"
  }'
```

### Шаг 4: Проверить, что артефакт активирован
```bash
curl http://localhost:8000/api/artifacts/{artifact_id}
# status должен быть "active"
```

## 6. Тестирование отклонения запроса

```bash
curl -X POST http://localhost:8000/api/approvals/{request_id}/reject \
  -H "Content-Type: application/json" \
  -d '{
    "feedback": "Security concerns detected, needs review"
  }'
```

## 7. Тестирование модификации запроса

```bash
curl -X POST http://localhost:8000/api/approvals/{request_id}/modify \
  -H "Content-Type: application/json" \
  -d '{
    "modified_data": {
      "code": "def modified_function():\n    return 'modified'"
    },
    "feedback": "Made security improvements"
  }'
```

## Ожидаемые результаты

### При создании артефакта:
- ✅ Артефакт создается со статусом `waiting_approval`
- ✅ Автоматически создается запрос на утверждение
- ✅ Запрос появляется в `/api/approvals/`

### При утверждении:
- ✅ Статус артефакта меняется на `active`
- ✅ Статус запроса меняется на `approved`
- ✅ Артефакт доступен для использования

### При отклонении:
- ✅ Статус запроса меняется на `rejected`
- ✅ Артефакт остается в статусе `waiting_approval`

## Возможные проблемы

### 1. Ошибка подключения к БД
```
ValidationError: postgres_host Field required
```
**Решение:** Убедитесь, что `.env` файл существует и содержит все необходимые переменные.

### 2. Ошибка подключения к Ollama
```
OllamaError: Connection failed
```
**Решение:** Проверьте, что Ollama серверы доступны по указанным адресам.

### 3. Таймаут при создании артефакта
```
TimeoutException
```
**Решение:** Это нормально для больших моделей. Увеличьте timeout в клиенте или подождите дольше.

## Следующие шаги после тестирования

1. ✅ Создать веб-интерфейс для утверждений
2. ✅ Добавить обработку обратной связи
3. ✅ Реализовать эволюцию промптов
4. ✅ Интегрировать с системой памяти

