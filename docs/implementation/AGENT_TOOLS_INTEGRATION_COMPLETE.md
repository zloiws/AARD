# Интеграция агентов с инструментами - Завершено

## Обзор

Успешно интегрирована система инструментов с агентами. Теперь агенты могут находить, проверять доступ и использовать инструменты для выполнения задач.

## Реализованные компоненты

### 1. Обновлен BaseAgent (`app/agents/base_agent.py`)

Добавлены методы для работы с инструментами:

- **`get_available_tools(category=None)`** - получить список доступных инструментов
- **`get_tool_by_name(tool_name)`** - получить информацию об инструменте по имени
- **`use_tool(tool_name, **kwargs)`** - использовать инструмент для выполнения действия
- **`list_tools_by_category()`** - получить инструменты, сгруппированные по категориям

**Изменения:**
- Добавлен `ToolService` в конструктор
- Добавлена поддержка базы данных для работы с инструментами
- Интеграция с трассировкой OpenTelemetry
- Проверка доступа агента к инструменту
- Обработка ошибок при выполнении инструментов

### 2. Обновлен SimpleAgent (`app/agents/simple_agent.py`)

Добавлена поддержка использования инструментов:

- Параметр `use_tools` для включения информации об инструментах в промпт
- Параметр `tool_name` для прямого использования инструмента
- Автоматический fallback на LLM при ошибке инструмента
- Логирование использования инструментов

### 3. Документация

Создан файл `docs/guides/AGENT_TOOLS_INTEGRATION.md` с:
- Описанием архитектуры интеграции
- Примерами использования
- Лучшими практиками
- Обработкой ошибок

## Функциональность

### Поиск инструментов

```python
# Получить все доступные инструменты
tools = agent.get_available_tools()

# Получить инструменты по категории
file_tools = agent.get_available_tools(category="file_operations")

# Сгруппированные по категориям
categorized = agent.list_tools_by_category()
```

### Использование инструментов

```python
# Использовать инструмент
result = await agent.use_tool(
    tool_name="file_finder",
    directory="/path/to/dir",
    extension="py"
)

# Результат:
# {
#     "status": "success" | "failed",
#     "result": Any,
#     "message": str,
#     "metadata": Dict
# }
```

### Интеграция в выполнение задач

```python
# В SimpleAgent
result = await agent.execute(
    task_description="Find all Python files",
    tool_name="file_finder",
    tool_params={"directory": "/path", "extension": "py"}
)

# С автоматическим выбором
result = await agent.execute(
    task_description="Help with file operations",
    use_tools=True  # Agent sees available tools
)
```

## Проверка доступа

Система автоматически проверяет:
1. Статус инструмента (должен быть `active`)
2. Список запрещенных агентов (`forbidden_agents`)
3. Список разрешенных агентов (`allowed_agents`)
4. Права агента через `_check_permissions()`

## Трассировка

Все операции с инструментами трассируются:
- Span: `agent.use_tool`
- Атрибуты: agent.id, agent.name, tool.name, tool.success
- Метрики: execution_time_ms

## Примеры использования

### Базовое использование

```python
from app.agents.simple_agent import SimpleAgent
from app.services.agent_service import AgentService
from app.core.database import SessionLocal

db = SessionLocal()
agent_service = AgentService(db)
agent_data = agent_service.get_agent_by_name("my_agent")

agent = SimpleAgent(
    agent_id=agent_data.id,
    agent_service=agent_service,
    db_session=db
)

# Использовать инструмент
result = await agent.use_tool("file_finder", directory="/tmp", extension="py")
```

### Создание специализированного агента

```python
class FileAgent(BaseAgent):
    async def execute(self, task_description: str, **kwargs):
        if "find files" in task_description.lower():
            return await self.use_tool("file_finder", **kwargs)
        else:
            return await self._call_llm(prompt=task_description)
```

## Тестирование

Для тестирования интеграции:

1. Создать инструмент через API
2. Активировать инструмент
3. Создать агента
4. Настроить доступ агента к инструменту
5. Выполнить задачу через агента с использованием инструмента

## Следующие шаги

- [ ] Интеграция с планированием (использование инструментов в планах)
- [ ] Кэширование результатов инструментов
- [ ] Параллельное выполнение инструментов
- [ ] Цепочки инструментов (output одного -> input другого)
- [ ] Веб-интерфейс для управления доступом
- [ ] Тесты интеграции агентов и инструментов

## Файлы изменены

- `backend/app/agents/base_agent.py` - добавлены методы работы с инструментами
- `backend/app/agents/simple_agent.py` - добавлена поддержка инструментов
- `docs/guides/AGENT_TOOLS_INTEGRATION.md` - документация интеграции
- `docs/guides/README.md` - добавлена ссылка на документацию

## Статус

✅ **Интеграция завершена и готова к использованию**

Агенты теперь могут:
- Находить доступные инструменты
- Проверять права доступа
- Выполнять инструменты
- Комбинировать LLM и инструменты для решения задач

