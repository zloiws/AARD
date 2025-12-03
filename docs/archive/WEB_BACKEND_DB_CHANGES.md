# Изменения в веб-бэкенде для использования БД серверов

## ✅ Изменения выполнены

### 1. `backend/app/api/routes/pages.py`

**Изменено:**
- Заменен `OllamaClient` на `get_db()` dependency
- Загрузка серверов из БД через `OllamaService.get_all_active_servers(db)`
- Передача списка серверов в шаблон вместо списка моделей

**Было:**
```python
client: OllamaClient = Depends(get_ollama_client)
for instance in client.instances:  # Из .env
    models.append({...})
```

**Стало:**
```python
db: Session = Depends(get_db)
servers = OllamaService.get_all_active_servers(db)  # Из БД
for server in servers:
    servers_info.append({
        "id": str(server.id),
        "name": server.name,
        "url": server.url,
        "api_url": server.get_api_url(),
        ...
    })
```

### 2. `backend/app/api/routes/models.py`

**Изменено:**
- Заменен `OllamaClient` на `get_db()` dependency
- Загрузка серверов из БД через `OllamaService.get_all_active_servers(db)`
- Добавлены поля `id`, `name`, `is_default` в ответ

**Было:**
```python
client: OllamaClient = Depends(get_ollama_client)
for instance in client.instances:  # Из .env
```

**Стало:**
```python
db: Session = Depends(get_db)
servers_list = OllamaService.get_all_active_servers(db)  # Из БД
for server in servers_list:
    server_info = ServerInfo(
        id=str(server.id),
        name=server.name,
        ...
    )
```

### 3. `backend/app/api/routes/chat.py`

**Без изменений:**
- Уже использует `server_url` и `model` напрямую
- При указанном `server_url` и `model` создается динамический instance
- Работает корректно с новой логикой

## Структура данных

### Старый формат (из .env)
```json
{
  "models": [
    {
      "model": "huihui_ai/deepseek-r1-abliterated:8b",
      "url": "http://10.39.0.101:11434/v1",
      "capabilities": ["general", "reasoning"],
      "available": true
    }
  ]
}
```

### Новый формат (из БД)
```json
{
  "servers": [
    {
      "id": "uuid",
      "name": "Server 1 - General/Reasoning",
      "url": "http://10.39.0.101:11434",
      "api_url": "http://10.39.0.101:11434/v1",
      "capabilities": ["general", "reasoning"],
      "is_available": true,
      "is_default": true
    }
  ]
}
```

## API изменения

### `/api/models/servers`
Теперь возвращает серверы из БД с дополнительными полями:
- `id` - UUID сервера
- `name` - имя сервера
- `is_default` - флаг сервера по умолчанию
- `api_url` - полный URL API

## Следующие шаги

1. ✅ Бэкенд обновлен - использует БД
2. ⏳ Фронтенд - может потребоваться обновление для работы с новым форматом
3. ⏳ Тестирование - проверить работу выбора серверов и моделей

## Примечания

- Фронтенд загружает серверы через API `/api/models/servers`, который уже обновлен
- Шаблон `index_new.html` получает список `servers` вместо `models`
- Функция `loadServers()` во фронтенде должна работать с новым форматом данных

