# Интеграция агентов с инструментами

## Обзор

Агенты в AARD могут использовать инструменты (tools) для выполнения действий. Интеграция позволяет агентам:
- Находить доступные инструменты
- Проверять права доступа к инструментам
- Выполнять инструменты для решения задач
- Комбинировать LLM и инструменты

## Архитектура

### Компоненты

1. **BaseAgent** (`app/agents/base_agent.py`)
   - Базовый класс для всех агентов
   - Методы для работы с инструментами
   - Проверка доступа и выполнение

2. **ToolService** (`app/services/tool_service.py`)
   - Управление инструментами
   - Проверка доступа агентов

3. **PythonTool** (`app/tools/python_tool.py`)
   - Выполнение Python инструментов

## Использование инструментов в агентах

### Базовые методы

#### Получение доступных инструментов

```python
# Получить все доступные инструменты
tools = agent.get_available_tools()

# Получить инструменты по категории
file_tools = agent.get_available_tools(category="file_operations")

# Получить инструменты, сгруппированные по категориям
categorized = agent.list_tools_by_category()
```

#### Использование инструмента

```python
# Использовать инструмент по имени
result = await agent.use_tool(
    tool_name="file_finder",
    directory="/path/to/dir",
    extension="py"
)

# result содержит:
# {
#     "status": "success" | "failed",
#     "result": Any,
#     "message": str,
#     "metadata": Dict
# }
```

#### Получение информации об инструменте

```python
# Получить информацию об инструменте
tool_info = agent.get_tool_by_name("file_finder")
if tool_info:
    print(f"Tool: {tool_info['name']}")
    print(f"Description: {tool_info['description']}")
```

### Пример использования в агенте

```python
from app.agents.base_agent import BaseAgent
from app.services.agent_service import AgentService
from app.core.database import SessionLocal

class FileAgent(BaseAgent):
    """Agent specialized in file operations"""
    
    async def execute(self, task_description: str, context=None, **kwargs):
        # Check if task requires file operations
        if "find files" in task_description.lower():
            # Use file_finder tool
            result = await self.use_tool(
                tool_name="file_finder",
                directory=context.get("directory", "."),
                extension=context.get("extension")
            )
            
            if result["status"] == "success":
                return {
                    "status": "success",
                    "result": result["result"],
                    "message": "Files found successfully"
                }
        
        # Fall back to LLM
        return await self._call_llm(
            prompt=task_description,
            system_prompt="You are a file operations assistant."
        )
```

### Интеграция в SimpleAgent

`SimpleAgent` поддерживает использование инструментов:

```python
# Использовать инструмент напрямую
result = await agent.execute(
    task_description="Find all Python files",
    tool_name="file_finder",
    tool_params={"directory": "/path", "extension": "py"}
)

# Включить информацию об инструментах в промпт
result = await agent.execute(
    task_description="Help me with file operations",
    use_tools=True  # Agent will see available tools
)
```

## Проверка доступа

Система автоматически проверяет доступ агента к инструменту:

1. **Статус инструмента** - должен быть `active`
2. **Forbidden agents** - агент не должен быть в списке запрещенных
3. **Allowed agents** - если указан список, агент должен быть в нем
4. **Permissions** - проверка через `_check_permissions()`

### Настройка доступа

```python
# При создании инструмента
tool = tool_service.create_tool(
    name="sensitive_tool",
    # ...
    allowed_agents=[str(agent1.id), str(agent2.id)],  # Только эти агенты
    forbidden_agents=[str(agent3.id)]  # Этот агент запрещен
)
```

## Трассировка

Все операции с инструментами трассируются через OpenTelemetry:

- `agent.use_tool` - span для использования инструмента
- Атрибуты: agent.id, agent.name, tool.name, tool.success
- Метрики: execution_time_ms

## Обработка ошибок

Агенты должны обрабатывать ошибки при использовании инструментов:

```python
result = await agent.use_tool("tool_name", param="value")

if result["status"] == "failed":
    # Обработать ошибку
    error_msg = result["message"]
    # Fallback на LLM или другой инструмент
```

## Примеры

### Агент для работы с файлами

```python
class FileOperationsAgent(BaseAgent):
    async def execute(self, task_description: str, **kwargs):
        # Определить тип операции
        if "find" in task_description.lower():
            return await self.use_tool("file_finder", **kwargs)
        elif "read" in task_description.lower():
            return await self.use_tool("file_reader", **kwargs)
        else:
            # Использовать LLM для других задач
            return await self._call_llm(prompt=task_description)
```

### Агент с автоматическим выбором инструмента

```python
class SmartAgent(BaseAgent):
    async def execute(self, task_description: str, **kwargs):
        # Получить доступные инструменты
        tools = self.get_available_tools()
        
        # Попытаться найти подходящий инструмент
        for tool in tools:
            if tool["name"] in task_description.lower():
                result = await self.use_tool(tool["name"], **kwargs)
                if result["status"] == "success":
                    return result
        
        # Fallback на LLM
        return await self._call_llm(prompt=task_description)
```

## Лучшие практики

1. **Всегда проверяйте результат** - инструменты могут завершиться ошибкой
2. **Используйте fallback** - если инструмент не работает, используйте LLM
3. **Логируйте использование** - для отладки и мониторинга
4. **Валидируйте входные данные** - перед вызовом инструмента
5. **Обрабатывайте таймауты** - инструменты могут долго выполняться

## Следующие шаги

- [ ] Интеграция с планированием (использование инструментов в планах)
- [ ] Кэширование результатов инструментов
- [ ] Параллельное выполнение инструментов
- [ ] Цепочки инструментов (output одного -> input другого)
- [ ] Веб-интерфейс для управления доступом агентов к инструментам

