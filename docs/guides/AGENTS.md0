# Агенты в AARD

## Обзор

Агенты в AARD - это автономные сущности, которые могут выполнять задачи, использовать инструменты и взаимодействовать друг с другом. Каждый агент имеет свою специализацию, конфигурацию и метрики производительности.

## Архитектура

### Компоненты

1. **Agent Model** (`app/models/agent.py`)
   - Модель данных для хранения информации об агентах
   - Статусы: draft, waiting_approval, active, paused, deprecated, failed
   - Ка capabilities: code_generation, code_analysis, planning, reasoning, etc.

2. **AgentService** (`app/services/agent_service.py`)
   - Управление жизненным циклом агентов
   - CRUD операции
   - Метрики и статистика

3. **BaseAgent** (`app/agents/base_agent.py`)
   - Базовый класс для всех агентов
   - Абстрактный метод `execute()` для реализации в подклассах
   - Интеграция с LLM, логированием, трассировкой

4. **API** (`app/api/routes/agents.py`)
   - REST API для управления агентами
   - CRUD endpoints
   - Управление статусами
   - Метрики

## Создание агента

### Через API

```bash
POST /api/agents/
Content-Type: application/json

{
  "name": "code_generator",
  "description": "Agent for generating code",
  "system_prompt": "You are a code generation agent. Generate clean, efficient code.",
  "capabilities": ["code_generation", "code_analysis"],
  "model_preference": "qwen3-coder:30b-a3b-q4_K_M",
  "temperature": "0.7",
  "max_concurrent_tasks": 2,
  "tags": ["coding", "generation"]
}
```

### Через код

```python
from app.services.agent_service import AgentService
from app.core.database import get_db

db = next(get_db())
service = AgentService(db)

agent = service.create_agent(
    name="code_generator",
    description="Agent for generating code",
    system_prompt="You are a code generation agent...",
    capabilities=["code_generation"],
    model_preference="qwen3-coder:30b-a3b-q4_K_M",
    created_by="user@example.com"
)
```

## Использование агента

### Базовое использование

```python
from app.agents.simple_agent import SimpleAgent
from app.services.agent_service import AgentService
from app.core.database import get_db

db = next(get_db())
agent_service = AgentService(db)

# Get agent ID
agent_id = UUID("...")

# Create agent instance
agent = SimpleAgent(
    agent_id=agent_id,
    agent_service=agent_service
)

# Execute task
result = await agent.execute(
    task_description="Generate a Python function to calculate factorial",
    context={"language": "python", "style": "clean"}
)

print(result["result"])
```

## Статусы агентов

- **draft** - Агент создан, но не готов к использованию
- **waiting_approval** - Ожидает утверждения человеком
- **active** - Активен и готов к выполнению задач
- **paused** - Временно приостановлен
- **deprecated** - Устарел, не используется
- **failed** - Ошибка при активации или выполнении

## Ка capabilities

Агенты могут иметь следующие capabilities:

- `code_generation` - Генерация кода
- `code_analysis` - Анализ кода
- `planning` - Планирование задач
- `reasoning` - Логические рассуждения
- `data_processing` - Обработка данных
- `text_generation` - Генерация текста
- `research` - Исследования
- `testing` - Тестирование
- `deployment` - Развертывание
- `monitoring` - Мониторинг

## Безопасность

### Политики безопасности

Агенты могут иметь политики безопасности:

```python
agent = service.update_agent(
    agent_id=agent_id,
    security_policies={
        "max_execution_time": 300,  # seconds
        "allowed_file_types": [".py", ".js"],
        "forbidden_operations": ["delete", "modify_system"]
    },
    allowed_actions=["read", "write", "execute"],
    forbidden_actions=["delete", "modify_system"]
)
```

### Проверка разрешений

```python
# In agent implementation
if not self._check_permissions("write_file"):
    raise PermissionError("Agent not allowed to write files")
```

## Метрики

### Получение метрик

```bash
GET /api/agents/{agent_id}/metrics
```

Response:
```json
{
  "total_tasks_executed": 150,
  "successful_tasks": 142,
  "failed_tasks": 8,
  "success_rate": "94.67%",
  "average_execution_time": 5,
  "last_used_at": "2025-12-03T10:30:00"
}
```

### Автоматический сбор

Метрики собираются автоматически при каждом выполнении задачи через `_record_execution()`.

## Создание специализированного агента

### Пример: Code Generation Agent

```python
from app.agents.base_agent import BaseAgent
from app.core.ollama_client import TaskType

class CodeGenerationAgent(BaseAgent):
    """Specialized agent for code generation"""
    
    async def execute(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        # Custom logic for code generation
        prompt = f"Generate code for: {task_description}"
        
        if context:
            prompt += f"\nRequirements: {context.get('requirements', '')}"
            prompt += f"\nLanguage: {context.get('language', 'python')}"
        
        response = await self._call_llm(
            prompt=prompt,
            task_type=TaskType.CODE_GENERATION,
            **kwargs
        )
        
        # Post-process response
        code = self._extract_code(response)
        
        return {
            "status": "success",
            "result": code,
            "message": "Code generated successfully",
            "metadata": {"language": context.get("language", "python")}
        }
    
    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response"""
        # Implementation for code extraction
        import re
        code_blocks = re.findall(r'```(?:python|javascript|.*)?\n(.*?)```', response, re.DOTALL)
        return code_blocks[0] if code_blocks else response
```

## Интеграция с планированием

Агенты могут быть назначены на выполнение шагов плана:

```python
# In execution_service.py
if step.get("agent_id"):
    agent = SimpleAgent(
        agent_id=UUID(step["agent_id"]),
        agent_service=AgentService(self.db)
    )
    result = await agent.execute(
        task_description=step["description"],
        context=execution_context
    )
```

## API Endpoints

### Создание агента
```
POST /api/agents/
```

### Список агентов
```
GET /api/agents/?status=active&capability=code_generation
```

### Получение агента
```
GET /api/agents/{agent_id}
```

### Обновление агента
```
PUT /api/agents/{agent_id}
```

### Активация агента
```
POST /api/agents/{agent_id}/activate
```

### Пауза агента
```
POST /api/agents/{agent_id}/pause
```

### Устаревание агента
```
POST /api/agents/{agent_id}/deprecate
```

### Метрики агента
```
GET /api/agents/{agent_id}/metrics
```

## Следующие шаги

- [ ] A2A взаимодействие (Agent-to-Agent communication)
- [ ] Интеграция с инструментами (Tools)
- [ ] Heartbeat механизм для health checks
- [ ] Версионирование агентов
- [ ] A/B тестирование агентов
- [ ] Agent Gym для тестирования

