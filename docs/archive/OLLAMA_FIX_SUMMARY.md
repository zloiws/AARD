# Исправление логики вызова моделей Ollama

## Проблемы, которые были исправлены:

### 1. ❌ `selected_server` не был определен
**Ошибка:** `name 'selected_server' is not defined`
**Исправлено:** Добавлено определение `selected_server` из `chat_message.server`

### 2. ❌ Неправильный формат API запросов
**Проблема:** Использовался старый формат `/api/generate` с `prompt` вместо `/api/chat` с `messages`
**Исправлено:** 
- Переход на `/api/chat` endpoint
- Использование формата `messages` с ролями (system, user, assistant)
- Правильная структура запроса для Ollama Chat API

### 3. ❌ История чата не передавалась
**Проблема:** История из сессии не передавалась в модель
**Исправлено:**
- Добавлен метод `get_ollama_history()` в `ChatSessionManager`
- История теперь передается в `generate()` и `generate_stream()`
- System prompt правильно включается в историю

## Изменения в коде:

### `backend/app/api/routes/chat.py`
- Добавлено определение `selected_server` из `chat_message.server`
- Передача `system_prompt` и `history` в `client.generate()`
- Исправлена передача параметров в `_stream_generation()`

### `backend/app/core/ollama_client.py`
- Методы `generate()` и `generate_stream()` теперь принимают:
  - `system_prompt: Optional[str]`
  - `history: Optional[List[Dict[str, str]]]`
- Запросы теперь используют `/api/chat` вместо `/api/generate`
- Правильный формат payload с `messages` массивом:
  ```python
  {
    "model": "model-name",
    "messages": [
      {"role": "system", "content": "..."},
      {"role": "user", "content": "..."},
      {"role": "assistant", "content": "..."}
    ],
    "stream": true/false,
    "options": {...}
  }
  ```

### `backend/app/core/chat_session.py`
- Добавлен метод `get_ollama_history(session_id)` который:
  - Возвращает историю в формате Ollama
  - Включает system_prompt если есть
  - Конвертирует сообщения в формат `{"role": "...", "content": "..."}`

## Правильная логика работы:

1. **Сбор параметров:**
   - `selected_model` из `chat_message.model`
   - `selected_server` из `chat_message.server`
   - `system_prompt` из `chat_message.system_prompt` или сессии
   - `history` из сессии через `session_manager.get_ollama_history()`

2. **Выбор instance:**
   - Если указан `server_url`, сначала ищется instance по URL
   - Если не найден, создается временный instance для динамического сервера
   - Если сервер не указан, ищется по имени модели

3. **Формирование запроса:**
   - Используется `/api/chat` endpoint
   - Сообщения формируются: system → history → current user message
   - Правильный формат для Ollama Chat API

## Результат:

✅ Все запросы теперь используют правильный формат Ollama Chat API
✅ История чата передается и используется моделью
✅ System prompts работают корректно
✅ Выбор сервера работает правильно

