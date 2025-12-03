# Реализация системы инструментов (Tools)

## Обзор

Реализована полная система инструментов для AARD платформы, позволяющая создавать, управлять и выполнять инструменты, которые агенты могут использовать для выполнения действий.

## Реализованные компоненты

### 1. Модель данных (`app/models/tool.py`)

- **Tool** - основная модель инструмента
  - Идентификация: id, name, description, category
  - Версионирование: version, parent_tool_id
  - Жизненный цикл: status, created_at, updated_at, activated_at, last_used_at
  - Реализация: code, entry_point, language
  - Схемы: input_schema, output_schema, parameters
  - Зависимости: dependencies, requirements
  - Безопасность: security_policies, allowed_agents, forbidden_agents, requires_approval
  - Лимиты: timeout_seconds, max_memory_mb, rate_limit_per_minute
  - Метрики: total_executions, successful_executions, failed_executions, average_execution_time, success_rate
  - Метаданные: tool_metadata, tags, examples

### 2. Сервис управления (`app/services/tool_service.py`)

- **ToolService** - сервис для управления инструментами
  - `create_tool()` - создание нового инструмента
  - `get_tool()` - получение инструмента по ID
  - `get_tool_by_name()` - получение инструмента по имени
  - `list_tools()` - список инструментов с фильтрами
  - `update_tool()` - обновление свойств инструмента
  - `activate_tool()` - активация инструмента
  - `pause_tool()` - приостановка инструмента
  - `deprecate_tool()` - устаревание инструмента
  - `record_execution()` - запись выполнения для метрик
  - `get_tool_metrics()` - получение метрик инструмента
  - `can_agent_use_tool()` - проверка доступа агента к инструменту

### 3. Базовый класс (`app/tools/base_tool.py`)

- **BaseTool** - абстрактный базовый класс для всех инструментов
  - Загрузка данных инструмента из БД
  - Абстрактный метод `execute()` для выполнения
  - `execute_python_code()` - выполнение Python кода динамически
  - `validate_input()` - валидация входных параметров по схеме
  - Интеграция с логированием и трассировкой

### 4. Реализация Python инструмента (`app/tools/python_tool.py`)

- **PythonTool** - реализация для Python инструментов
  - Наследуется от `BaseTool`
  - Выполняет Python код из поля `code`
  - Валидация входных данных
  - Обработка ошибок

### 5. API Endpoints (`app/api/routes/tools.py`)

- `POST /api/tools/` - создание инструмента
- `GET /api/tools/` - список инструментов (с фильтрами)
- `GET /api/tools/{tool_id}` - получение инструмента
- `PUT /api/tools/{tool_id}` - обновление инструмента
- `POST /api/tools/{tool_id}/activate` - активация инструмента
- `POST /api/tools/{tool_id}/pause` - приостановка инструмента
- `POST /api/tools/{tool_id}/deprecate` - устаревание инструмента
- `GET /api/tools/{tool_id}/metrics` - метрики инструмента
- `GET /api/tools/{tool_id}/can-use/{agent_id}` - проверка доступа агента

### 6. Миграция БД (`alembic/versions/010_add_tools.py`)

- Создание таблицы `tools` со всеми полями
- Индексы для быстрого поиска
- Внешний ключ для parent_tool_id

### 7. Документация (`docs/guides/TOOLS.md`)

- Полное описание системы инструментов
- Примеры использования
- API документация
- Интеграция с агентами

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

## Безопасность

- Ограничение доступа по агентам (allowed_agents, forbidden_agents)
- Требование утверждения перед выполнением (requires_approval)
- Политики безопасности (security_policies)
- Таймауты и лимиты ресурсов

## Метрики

Автоматический сбор метрик:
- Общее количество выполнений
- Успешные/неуспешные выполнения
- Среднее время выполнения
- Процент успешности
- Последнее использование

## Следующие шаги

1. **Применить миграцию БД:**
   ```bash
   cd backend && alembic upgrade head
   ```

2. **Протестировать API:**
   - Создать инструмент через API
   - Выполнить инструмент
   - Проверить метрики

3. **Интеграция с агентами:**
   - Добавить использование инструментов в `BaseAgent`
   - Создать примеры агентов, использующих инструменты

4. **Веб-интерфейс:**
   - Создать UI для управления инструментами
   - Просмотр метрик и статистики

5. **Дополнительные функции:**
   - Sandbox для безопасного выполнения
   - Поддержка других языков (JavaScript, etc.)
   - Кэширование результатов
   - Версионирование инструментов
   - Автоматическое тестирование инструментов

## Пример использования

```python
from app.services.tool_service import ToolService
from app.tools.python_tool import PythonTool
from app.core.database import get_db

# Создать инструмент
db = next(get_db())
service = ToolService(db)

tool = service.create_tool(
    name="file_finder",
    description="Find files by extension",
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

# Активировать инструмент
service.activate_tool(tool.id)

# Выполнить инструмент
python_tool = PythonTool(tool_id=tool.id, tool_service=service)
result = await python_tool.execute(directory="/path/to/dir", extension="py")
```

