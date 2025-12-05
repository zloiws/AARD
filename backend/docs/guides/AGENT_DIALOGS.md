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

## AgentDialogService

Сервис для управления диалогами между агентами.

### Основные методы

#### Создание диалога

```python
from app.services.agent_dialog_service import AgentDialogService

service = AgentDialogService(db)

conversation = service.create_conversation(
    participant_ids=[agent1.id, agent2.id],
    goal="Решить сложную задачу",
    title="Диалог о планировании",
    task_id=task.id  # Опционально
)
```

#### Добавление сообщений

```python
# Простое добавление сообщения
message = service.add_message(
    conversation_id=conversation.id,
    agent_id=agent1.id,
    content="Привет! Давай обсудим задачу.",
    role=MessageRole.AGENT
)

# Отправка сообщения с уведомлением других участников через A2A
message = await service.send_message_to_participants(
    conversation_id=conversation.id,
    sender_agent_id=agent1.id,
    content="Важное сообщение",
    recipient_agent_ids=[agent2.id]  # Опционально, если None - всем остальным
)
```

#### Управление контекстом

```python
# Обновить контекст
context = service.update_context(
    conversation_id=conversation.id,
    updates={
        "shared_knowledge": "Важная информация",
        "intermediate_result": "Промежуточный результат"
    }
)
```

#### Проверка завершения

```python
# Проверить, завершен ли диалог
is_complete = service.is_conversation_complete(
    conversation_id=conversation.id,
    check_conditions={
        "max_messages": 10,  # Максимум сообщений
        "min_messages": 3,   # Минимум сообщений
        "timeout_seconds": 300,  # Таймаут в секундах
        "goal_achieved": True  # Цель достигнута
    }
)
```

#### Завершение диалога

```python
# Завершить диалог
completed = service.complete_conversation(
    conversation_id=conversation.id,
    success=True,
    result={"outcome": "success", "plan": "..."}
)
```

#### Пауза и возобновление

```python
# Приостановить диалог
paused = service.pause_conversation(conversation.id)

# Возобновить диалог
resumed = service.resume_conversation(conversation.id)
```

#### Поиск диалогов

```python
# Получить диалоги по задаче
conversations = service.get_conversations_by_task(task.id)

# Получить диалоги агента
conversations = service.get_conversations_by_agent(agent.id)
```

### Интеграция с A2A протоколом

`AgentDialogService` автоматически отправляет A2A сообщения другим участникам при использовании `send_message_to_participants()`. Это позволяет агентам получать уведомления о новых сообщениях в диалоге.

## Следующие шаги

- ✅ Реализация `AgentDialogService` для управления диалогами (выполнено)
- Интеграция диалогов в `PlanningService`
- API для управления диалогами
- Полный цикл диалога с реальными агентами

