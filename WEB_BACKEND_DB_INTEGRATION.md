# Интеграция БД серверов в веб-бэкенд

## Изменения

### 1. ✅ Обновлен `backend/app/api/routes/pages.py`

**Было:** Загружал серверы из .env через `OllamaClient.instances`

**Стало:** Загружает серверы из БД через `OllamaService.get_all_active_servers(db)`

```python
# Теперь передает список серверов из БД в шаблон
servers = OllamaService.get_all_active_servers(db)
servers_info = [{
    "id": str(server.id),
    "name": server.name,
    "url": server.url,
    "api_url": server.get_api_url(),
    "capabilities": server.capabilities or [],
    "is_available": server.is_available,
    "is_default": server.is_default
} for server in servers]
```

### 2. ✅ Обновлен `backend/app/api/routes/models.py`

**Было:** Загружал серверы из .env через `OllamaClient.instances`

**Стало:** Загружает серверы из БД через `OllamaService.get_all_active_servers(db)`

```python
@router.get("/servers")
async def list_servers(db: Session = Depends(get_db)):
    """Get list of Ollama servers from database"""
    servers_list = OllamaService.get_all_active_servers(db)
    # ... получает модели с каждого сервера через API
```

### 3. ✅ `backend/app/api/routes/chat.py` - без изменений

Эндпоинт `/api/chat/` уже использует `server_url` и `model` напрямую, поэтому он работает корректно:
- При указанном `server_url` и `model` создается динамический instance
- Используется именно запрошенная модель, без fallback на .env

## Результат

Теперь веб-бэкенд полностью использует серверы из БД:

1. **Страница `/`** - показывает серверы из БД
2. **API `/api/models/servers`** - возвращает серверы из БД с их моделями
3. **API `/api/chat/`** - использует указанный `server_url` и `model` напрямую

## Следующие шаги

1. Обновить фронтенд, чтобы он корректно работал с новым форматом данных серверов
2. Протестировать выбор сервера и модели в UI
3. Убедиться, что все запросы работают с серверами из БД

