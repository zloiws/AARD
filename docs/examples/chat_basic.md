# Пример: Базовое использование чата

## Сценарий

Отправка простого сообщения в чат и получение ответа от LLM.

## Запрос

### cURL

```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Привет, как дела?",
    "task_type": "general_chat"
  }'
```

### Python

```python
import requests

response = requests.post(
    "http://localhost:8000/api/chat/",
    json={
        "message": "Привет, как дела?",
        "task_type": "general_chat"
    }
)

data = response.json()
print(data["response"])
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://localhost:8000/api/chat/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: 'Привет, как дела?',
    task_type: 'general_chat'
  })
});

const data = await response.json();
console.log(data.response);
```

## Ответ

```json
{
  "response": "Привет! У меня все отлично, спасибо! Чем могу помочь?",
  "model": "deepseek-r1-abliterated:8b",
  "task_type": "general_chat",
  "duration_ms": 1234,
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "trace_id": "650e8400-e29b-41d4-a716-446655440001",
  "workflow_id": "750e8400-e29b-41d4-a716-446655440002"
}
```

## Обработка ошибок

```python
try:
    response = requests.post(...)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.HTTPError as e:
    print(f"HTTP Error: {e}")
except requests.exceptions.RequestException as e:
    print(f"Request Error: {e}")
```

