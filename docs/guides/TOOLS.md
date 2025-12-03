# Система инструментов (Tools)

## Обзор

Система инструментов AARD позволяет создавать, управлять и выполнять инструменты (tools) - исполняемые функции, которые агенты могут использовать для выполнения действий.

## Архитектура

### Компоненты

1. **Tool Model** (`app/models/tool.py`)
   - Модель данных для инструментов
   - Хранит код, схемы, метрики, безопасность

2. **ToolService** (`app/services/tool_service.py`)
   - Управление жизненным циклом инструментов
   - CRUD операции
   - Метрики и статистика

3. **BaseTool** (`app/tools/base_tool.py`)
   - Базовый класс для всех инструментов
   - Выполнение Python кода
   - Валидация входных данных

4. **PythonTool** (`app/tools/python_tool.py`)
   - Реализация для Python инструментов
   - Динамическое выполнение кода

5. **Tools API** (`app/api/routes/tools.py`)
   - REST API для управления инструментами

## Модель данных

### Tool

```python
{
    "id": UUID,
    "name": str,  # Уникальное имя
    "description": str,
    "category": str,  # file_operations, network, database, etc.
    "version": int,
    "status": str,  # draft, waiting_approval, active, paused, deprecated, failed
    "code": str,  # Python код инструмента
    "entry_point": str,  # Имя функции для вызова (по умолчанию: "execute")
    "language": str,  # python, javascript, etc.
    "input_schema": dict,  # JSON Schema для входных параметров
    "output_schema": dict,  # JSON Schema для выходных данных
    "parameters": list,  # Упрощенные определения параметров
    "dependencies": list,  # Список требуемых пакетов
    "requirements": str,  # requirements.txt содержимое
    "security_policies": dict,
    "allowed_agents": list,  # Список ID агентов, которым разрешено использовать
    "forbidden_agents": list,  # Список ID агентов, которым запрещено использовать
    "requires_approval": bool,  # Требовать утверждение перед выполнением
    "timeout_seconds": int,  # Таймаут выполнения
    "max_memory_mb": int,  # Лимит памяти
    "rate_limit_per_minute": int,  # Ограничение частоты вызовов
    "total_executions": int,
    "successful_executions": int,
    "failed_executions": int,
    "average_execution_time": int,  # в миллисекундах
    "success_rate": str,  # Процент успешных выполнений
    "metadata": dict,
    "tags": list,
    "examples": list
}
```

## Категории инструментов

- `file_operations` - Операции с файлами
- `network` - Сетевые операции
- `database` - Работа с БД
- `code_generation` - Генерация кода
- `code_analysis` - Анализ кода
- `data_processing` - Обработка данных
- `search` - Поиск
- `api` - API вызовы
- `system` - Системные операции
- `custom` - Пользовательские

## Статусы инструментов

- `draft` - Черновик
- `waiting_approval` - Ожидает утверждения
- `active` - Активен (можно использовать)
- `paused` - Приостановлен
- `deprecated` - Устарел
- `failed` - Ошибка

## API Endpoints

### Создание инструмента

```http
POST /api/tools/
Content-Type: application/json

{
    "name": "file_finder",
    "description": "Find files by extension and name",
    "category": "file_operations",
    "code": "def execute(directory, extension=None, name_pattern=None):\n    # Implementation\n    return {'files': []}",
    "entry_point": "execute",
    "input_schema": {
        "type": "object",
        "properties": {
            "directory": {"type": "string"},
            "extension": {"type": "string"},
            "name_pattern": {"type": "string"}
        },
        "required": ["directory"]
    },
    "dependencies": ["pathlib"],
    "timeout_seconds": 30
}
```

### Список инструментов

```http
GET /api/tools/?status=active&category=file_operations
```

### Получение инструмента

```http
GET /api/tools/{tool_id}
```

### Обновление инструмента

```http
PUT /api/tools/{tool_id}
Content-Type: application/json

{
    "description": "Updated description",
    "code": "def execute(...): ..."
}
```

### Активация инструмента

```http
POST /api/tools/{tool_id}/activate
```

### Метрики инструмента

```http
GET /api/tools/{tool_id}/metrics
```

### Проверка доступа агента

```http
GET /api/tools/{tool_id}/can-use/{agent_id}
```

## Использование в коде

### Создание инструмента через сервис

```python
from app.services.tool_service import ToolService
from app.core.database import get_db

db = next(get_db())
service = ToolService(db)

tool = service.create_tool(
    name="file_finder",
    description="Find files",
    category="file_operations",
    code="""
def execute(directory, extension=None):
    from pathlib import Path
    path = Path(directory)
    if extension:
        return list(path.glob(f"*.{extension}"))
    return list(path.glob("*"))
    """,
    entry_point="execute",
    input_schema={
        "type": "object",
        "properties": {
            "directory": {"type": "string"},
            "extension": {"type": "string"}
        },
        "required": ["directory"]
    }
)
```

### Выполнение инструмента

```python
from app.tools.python_tool import PythonTool
from app.services.tool_service import ToolService
from app.core.database import get_db

db = next(get_db())
service = ToolService(db)

# Создать экземпляр инструмента
tool = PythonTool(tool_id=tool.id, tool_service=service)

# Выполнить инструмент
result = await tool.execute(
    directory="/path/to/dir",
    extension="py"
)

print(result)
# {
#     "status": "success",
#     "result": [...],
#     "message": "Tool executed successfully",
#     "metadata": {...}
# }
```

### Проверка доступа агента

```python
can_use = service.can_agent_use_tool(
    tool_id=tool.id,
    agent_id=agent.id
)
```

## Безопасность

### Ограничения доступа

Инструменты могут ограничивать доступ:

- **allowed_agents** - только указанные агенты могут использовать
- **forbidden_agents** - указанные агенты не могут использовать
- **requires_approval** - требуется утверждение перед выполнением

### Политики безопасности

```python
tool = service.update_tool(
    tool_id=tool.id,
    security_policies={
        "sandbox": True,
        "network_access": False,
        "file_system_read": True,
        "file_system_write": False
    },
    allowed_agents=[str(agent1.id), str(agent2.id)]
)
```

## Метрики и мониторинг

Инструменты автоматически собирают метрики:

- Общее количество выполнений
- Успешные/неуспешные выполнения
- Среднее время выполнения
- Процент успешности

```python
metrics = service.get_tool_metrics(tool_id)
# {
#     "total_executions": 100,
#     "successful_executions": 95,
#     "failed_executions": 5,
#     "success_rate": "95.00%",
#     "average_execution_time": 150,
#     "last_used_at": "2025-12-03T10:00:00"
# }
```

## Интеграция с агентами

Агенты могут использовать инструменты через `BaseAgent`:

```python
from app.agents.base_agent import BaseAgent
from app.tools.python_tool import PythonTool

class MyAgent(BaseAgent):
    async def execute(self, task, context):
        # Получить инструмент
        tool_service = ToolService(self.db)
        tool_data = tool_service.get_tool_by_name("file_finder")
        
        # Создать экземпляр инструмента
        tool = PythonTool(tool_id=tool_data.id, tool_service=tool_service)
        
        # Выполнить инструмент
        result = await tool.execute(directory="/path")
        
        return result
```

## Примеры инструментов

### Поиск файлов

```python
code = """
def execute(directory, extension=None, name_pattern=None, recursive=True):
    from pathlib import Path
    import re
    
    path = Path(directory)
    if not path.exists():
        return {"error": "Directory not found"}
    
    files = []
    if recursive:
        pattern = "**/*"
    else:
        pattern = "*"
    
    for file_path in path.glob(pattern):
        if file_path.is_file():
            if extension and file_path.suffix != f".{extension}":
                continue
            if name_pattern and not re.search(name_pattern, file_path.name):
                continue
            files.append(str(file_path))
    
    return {"files": files, "count": len(files)}
"""
```

### HTTP запрос

```python
code = """
def execute(url, method="GET", headers=None, data=None):
    import httpx
    
    with httpx.Client() as client:
        response = client.request(
            method=method,
            url=url,
            headers=headers or {},
            json=data
        )
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text
        }
"""
```

## Следующие шаги

- [ ] Интеграция с системой утверждений
- [ ] Sandbox для безопасного выполнения
- [ ] Поддержка других языков (JavaScript, etc.)
- [ ] Кэширование результатов
- [ ] Версионирование инструментов
- [ ] Тестирование инструментов
- [ ] Веб-интерфейс для управления инструментами

