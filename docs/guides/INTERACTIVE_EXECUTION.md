# Interactive Execution Service

## Обзор

InteractiveExecutionService обеспечивает интерактивный контроль выполнения планов с возможностью паузы, уточнений и применения человеческих корректировок.

## Концепция

Во время выполнения плана система может:
- Приостановить выполнение для уточнения
- Применить человеческие корректировки
- Возобновить выполнение после обратной связи

## Основные методы

### execute_with_human_oversight

Выполнение шага с возможностью человеческого контроля:

```python
from app.services.interactive_execution_service import InteractiveExecutionService

service = InteractiveExecutionService(db)

result = await service.execute_with_human_oversight(
    step=step_definition,
    plan_id=plan_id,
    human_feedback_callback=callback_function
)
```

### pause_for_clarification

Приостановка выполнения для уточнения:

```python
result = service.pause_for_clarification(
    plan_id=plan_id,
    step_id="step_1",
    question="Do you want to proceed with this step?"
)
```

### apply_human_correction

Применение человеческой корректировки:

```python
correction = {
    "updated_step": {
        "description": "Updated description",
        "parameters": {"key": "value"}
    }
}

result = service.apply_human_correction(
    plan_id=plan_id,
    step_id="step_1",
    correction=correction
)
```

### resume_execution

Возобновление выполнения после паузы:

```python
result = service.resume_execution(
    plan_id=plan_id,
    feedback="Proceed with execution"
)
```

## Состояния выполнения

- `running` - выполнение активно
- `paused` - выполнение приостановлено
- `waiting_clarification` - ожидание уточнения
- `waiting_correction` - ожидание корректировки
- `resumed` - выполнение возобновлено
- `completed` - выполнение завершено
- `failed` - выполнение провалено

## API Endpoints

### POST /api/plans/{plan_id}/pause

Приостановить выполнение для уточнения:

```json
{
  "step_id": "step_1",
  "question": "Do you want to proceed?"
}
```

### POST /api/plans/{plan_id}/apply-correction

Применить человеческую корректировку:

```json
{
  "step_id": "step_1",
  "correction": {
    "updated_step": {
      "description": "Updated description"
    }
  }
}
```

### POST /api/plans/{plan_id}/resume

Возобновить выполнение:

```json
{
  "feedback": "Proceed with execution"
}
```

### GET /api/plans/{plan_id}/execution-state

Получить текущее состояние выполнения:

```json
{
  "state": "waiting_clarification",
  "step_id": "step_1",
  "question": "Do you want to proceed?",
  "paused_at": "2025-12-03T12:00:00Z"
}
```

## Интеграция

InteractiveExecutionService может быть интегрирован в ExecutionService для автоматической паузы при необходимости:

```python
# В ExecutionService._execute_action_step():
if step.get("requires_clarification", False):
    interactive_service = InteractiveExecutionService(self.db)
    interactive_service.pause_for_clarification(
        plan_id=plan.id,
        step_id=step_id,
        question=step.get("clarification_question")
    )
    # Wait for human feedback...
```

## Примеры использования

### Пример 1: Пауза для уточнения

```python
service = InteractiveExecutionService(db)

# Приостановить выполнение
result = service.pause_for_clarification(
    plan_id=plan_id,
    step_id="step_1",
    question="This step will modify production data. Proceed?"
)

# Получить состояние
state = service.get_execution_state(plan_id)
# state["state"] == "waiting_clarification"

# Возобновить после получения ответа
service.resume_execution(plan_id, feedback="Yes, proceed")
```

### Пример 2: Применение корректировки

```python
# Применить корректировку к шагу
correction = {
    "updated_step": {
        "description": "Updated step description",
        "parameters": {
            "timeout": 60,
            "retry_count": 3
        }
    }
}

result = service.apply_human_correction(
    plan_id=plan_id,
    step_id="step_1",
    correction=correction
)
```

### Пример 3: Полный цикл интерактивного выполнения

```python
async def human_feedback_callback(question: str, step: dict) -> Optional[str]:
    """Callback для получения человеческой обратной связи"""
    # В реальном приложении это может быть UI или API вызов
    print(f"Question: {question}")
    response = input("Your answer: ")
    return response

# Выполнить с человеческим контролем
result = await service.execute_with_human_oversight(
    step=step_definition,
    plan_id=plan_id,
    human_feedback_callback=human_feedback_callback
)
```

## Тестирование

```bash
python -m pytest tests/integration/test_interactive_execution.py -v
```

## Преимущества

1. **Гибкость**: Возможность вмешательства человека в любой момент
2. **Безопасность**: Пауза перед критическими операциями
3. **Корректировка**: Применение человеческих исправлений на лету
4. **Прозрачность**: Полный контроль над состоянием выполнения

## Следующие шаги

- [x] Реализация InteractiveExecutionService
- [x] API endpoints для интерактивного контроля
- [x] Тестирование
- [ ] Интеграция в ExecutionService для автоматической паузы
- [ ] UI для интерактивного контроля
- [ ] WebSocket для real-time обновлений состояния

## См. также

- [Execution Service](../archive/PLAN_APPROVAL_INTEGRATION.md) - выполнение планов
- [Adaptive Approval](ADAPTIVE_APPROVAL.md) - адаптивные утверждения

