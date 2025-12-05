# Диалоги между агентами (Agent Conversations)

## Обзор

Система диалогов между агентами позволяет агентам общаться друг с другом для совместного решения сложных задач. Диалоги хранятся в базе данных и могут быть связаны с задачами.

## Модель AgentConversation

### Основные поля

- **id**: UUID - уникальный идентификатор диалога
- **title**: String (опционально) - название диалога
- **description**: Text (опционально) - описание диалога
- **participants**: JSONB - список UUID агентов-участников
- **messages**: JSONB - список сообщений в диалоге
- **context**: JSONB - контекст диалога (общие знания, состояние, промежуточные результаты)
- **goal**: Text (опционально) - цель диалога (что агенты пытаются достичь)
- **status**: String - статус диалога (initiated, active, paused, completed, failed, cancelled)
- **task_id**: UUID (опционально) - связь с задачей
- **created_at**, **updated_at**, **completed_at**: DateTime - временные метки

### Статусы диалога (ConversationStatus)

- `INITIATED` - диалог начат, ожидается первое сообщение
- `ACTIVE` - диалог активен, идет общение
- `PAUSED` - диалог временно приостановлен
- `COMPLETED` - диалог успешно завершен
- `FAILED` - диалог завершился с ошибкой
- `CANCELLED` - диалог отменен

### Роли сообщений (MessageRole)

- `AGENT` - сообщение от агента
- `SYSTEM` - системное сообщение
- `USER` - сообщение от пользователя (если пользователь участвует)

## Структура сообщений

Каждое сообщение в диалоге имеет следующую структуру:

```json
{
  "id": "message_uuid",
  "agent_id": "agent_uuid",
  "role": "agent|system|user",
  "content": "Текст сообщения",
  "timestamp": "2024-01-01T00:00:00",
  "metadata": {
    // Дополнительные метаданные
  }
}
```

## Использование модели

### Создание диалога

```python
from app.models.agent_conversation import AgentConversation, ConversationStatus
from app.models.agent import Agent

# Создать диалог между двумя агентами
conversation = AgentConversation(
    title="Диалог о решении задачи",
    participants=[str(agent1.id), str(agent2.id)],
    messages=[],
    goal="Решить сложную задачу планирования",
    status=ConversationStatus.INITIATED.value
)

db.add(conversation)
db.commit()
```

### Добавление сообщений

```python
from app.models.agent_conversation import MessageRole

# Добавить сообщение от агента
message = conversation.add_message(
    agent_id=agent1.id,
    content="Привет! Давай обсудим задачу.",
    role=MessageRole.AGENT
)

db.commit()
```

### Управление контекстом

```python
# Получить контекст
context = conversation.get_context()

# Обновить контекст
conversation.update_context({
    "shared_knowledge": "Важная информация",
    "intermediate_result": "Промежуточный результат"
})

db.commit()
```

### Завершение диалога

```python
# Успешное завершение
conversation.complete(success=True)

# Завершение с ошибкой
conversation.complete(success=False)

db.commit()
```

### Проверка участников

```python
# Получить список участников
participants = conversation.get_participants()

# Проверить, является ли агент участником
is_participant = conversation.is_participant(agent_id)
```

## Связь с задачами

Диалог может быть связан с задачей через поле `task_id`:

```python
conversation = AgentConversation(
    participants=[str(agent1.id), str(agent2.id)],
    messages=[],
    task_id=task.id  # Связь с задачей
)
```

## Миграция базы данных

Миграция `028_add_agent_conversations.py` создает таблицу `agent_conversations` с необходимыми индексами:

- Индекс на `task_id` для быстрого поиска диалогов по задаче
- Индекс на `status` для фильтрации по статусу
- Индекс на `created_at` для сортировки по времени создания

## Тестирование

Модель протестирована в `backend/tests/test_agent_conversation_model.py`:

- Создание диалога
- Добавление сообщений
- Управление участниками
- Управление контекстом
- Завершение диалога
- Связь с задачами
- Преобразование в словарь

## Следующие шаги

- Реализация `AgentDialogService` для управления диалогами
- Интеграция диалогов в `PlanningService`
- API для управления диалогами
- Интеграция с A2A протоколом для обмена сообщениями

