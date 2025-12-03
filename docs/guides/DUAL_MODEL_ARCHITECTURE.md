# Dual-Model Architecture

## Обзор

AARD использует архитектуру с двумя специализированными моделями (dual-model architecture), которая разделяет ответственность между планированием и выполнением кода. Это соответствует концепции "модель Размышлений" и "модель Кода" из архитектурного анализа самоусовершенствующихся агентных систем.

## Концепция

### Модель "Размышлений" (Planning Model)

**Назначение:** Стратегическое планирование, декомпозиция задач, анализ требований

**Capabilities:**
- `planning` - планирование задач
- `reasoning` - логические рассуждения
- `strategy` - разработка стратегий

**Используется в:**
- `PlanningService._analyze_task()` - анализ задачи и создание стратегии
- `PlanningService._decompose_task()` - декомпозиция задачи на шаги
- `DecisionPipeline` - планирование выполнения

**Примеры моделей:**
- `deepseek-r1` - модели с reasoning capabilities
- Другие модели с planning/reasoning capabilities

### Модель "Кода" (Code Model)

**Назначение:** Генерация исполняемого кода, анализ кода, выполнение технических задач

**Capabilities:**
- `code_generation` - генерация кода
- `code_analysis` - анализ кода
- `code` - общие возможности работы с кодом

**Используется в:**
- `ExecutionService._execute_action_step()` - выполнение шагов, требующих генерации кода
- Генерация кода для инструментов
- Выполнение технических задач

**Примеры моделей:**
- `qwen3-coder` - специализированные модели для кодирования
- Другие модели с code_generation capabilities

## ModelSelector

`ModelSelector` - централизованный сервис для выбора специализированных моделей.

### Основные методы

```python
from app.core.model_selector import ModelSelector
from app.core.database import SessionLocal

db = SessionLocal()
selector = ModelSelector(db)

# Получить модель для планирования
planning_model = selector.get_planning_model()
# Ищет модель с capabilities: planning, reasoning, strategy
# Fallback: любая доступная модель

# Получить модель для генерации кода
code_model = selector.get_code_model()
# Ищет модель с capabilities: code_generation, code_analysis, code
# Fallback: любая доступная модель

# Получить модель по конкретной capability
model = selector.get_model_by_capability("planning")

# Получить сервер для модели
server = selector.get_server_for_model(model)
```

### Приоритеты выбора

1. **Для планирования:**
   - Сначала ищет модель с `planning` capability
   - Затем модель с `reasoning` capability
   - Затем модель с `strategy` capability
   - Fallback: первая доступная модель

2. **Для кода:**
   - Сначала ищет модель с `code_generation` capability
   - Затем модель с `code_analysis` capability
   - Затем модель с `code` capability
   - Fallback: первая доступная модель

### Интеграция

ModelSelector интегрирован в:

- **PlanningService** - использует `get_planning_model()` для всех операций планирования
- **ExecutionService** - использует `get_code_model()` для генерации кода

## Преимущества

1. **Разделение ответственности:** Каждая модель специализируется на своей задаче
2. **Оптимизация:** Можно использовать разные модели для разных задач
3. **Гибкость:** Легко заменить одну модель, не затрагивая другую
4. **Масштабируемость:** Можно добавлять новые специализированные модели

## Настройка моделей

Модели настраиваются в базе данных через таблицу `ollama_models`:

```sql
-- Пример: модель для планирования
UPDATE ollama_models 
SET capabilities = '["planning", "reasoning"]'::jsonb
WHERE model_name = 'deepseek-r1';

-- Пример: модель для кода
UPDATE ollama_models 
SET capabilities = '["code_generation", "code_analysis"]'::jsonb
WHERE model_name = 'qwen3-coder';
```

## Примеры использования

### В PlanningService

```python
from app.core.model_selector import ModelSelector

model_selector = ModelSelector(self.db)
planning_model = model_selector.get_planning_model()

if not planning_model:
    raise ValueError("No suitable model found for planning")

server = model_selector.get_server_for_model(planning_model)
```

### В ExecutionService

```python
from app.core.model_selector import ModelSelector

model_selector = ModelSelector(self.db)
code_model = model_selector.get_code_model()

if not code_model:
    raise ValueError("No suitable model found for code execution")

server = model_selector.get_server_for_model(code_model)
```

## Тестирование

Тесты для ModelSelector находятся в `backend/tests/integration/test_model_selector.py`:

```bash
python -m pytest tests/integration/test_model_selector.py -v
```

## Function Calling Protocol

Для безопасного выполнения кода используется Function Calling Protocol, который обеспечивает структурированный интерфейс между моделью планирования и выполнением кода.

### Основные компоненты

1. **FunctionCall** - структурированное представление вызова функции
2. **FunctionCallProtocol** - протокол для создания, валидации и парсинга function calls

### Использование

```python
from app.core.function_calling import FunctionCallProtocol

# Создание function call
call = FunctionCallProtocol.create_function_call(
    function_name="code_execution_tool",
    parameters={
        "code": "print('Hello, World!')",
        "language": "python"
    },
    safety_checks=True
)

# Валидация
is_valid, issues = FunctionCallProtocol.validate_function_call(call)

# Парсинг из LLM ответа
call = FunctionCallProtocol.parse_function_call_from_llm(llm_response)
```

### Безопасность

Function Calling Protocol включает:
- Whitelist разрешенных функций
- Проверку обязательных параметров
- Валидацию по JSON schema
- Проверку на опасный код (os.system, eval, exec и т.д.)
- Обнаружение SQL injection в запросах

## Следующие шаги

- [x] Реализация ModelSelector
- [x] Интеграция в PlanningService
- [x] Интеграция в ExecutionService
- [x] Function Calling Protocol для безопасного выполнения кода
- [ ] CodeExecutionSandbox для изоляции выполнения
- [ ] Метрики использования моделей

## См. также

- [Ollama Integration](OLLAMA_INTEGRATION.md) - общая информация об интеграции с Ollama
- [Planning Service](../archive/PLANNING_API_TEST_RESULTS.md) - документация по планированию
- [Execution Service](../archive/PLAN_APPROVAL_INTEGRATION.md) - документация по выполнению

