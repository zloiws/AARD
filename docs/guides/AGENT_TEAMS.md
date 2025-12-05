# Agent Teams Guide

## Обзор

Система команд агентов (Agent Teams) позволяет группировать специализированных агентов для совместной работы над задачами. Команды обеспечивают координацию, распределение ролей и эффективное выполнение сложных задач.

## Модель AgentTeam

### Основные поля

- **id**: UUID - уникальный идентификатор команды
- **name**: String(255) - название команды (уникальное)
- **description**: Text - описание команды
- **roles**: JSONB - словарь ролей (role_name -> role_description)
- **coordination_strategy**: String(50) - стратегия координации
- **status**: String(50) - статус команды
- **created_by**: String(255) - создатель команды
- **created_at**: DateTime - дата создания
- **updated_at**: DateTime - дата обновления
- **team_metadata**: JSONB - дополнительные метаданные

### Стратегии координации

- **sequential**: Агенты работают последовательно, один за другим
- **parallel**: Агенты работают параллельно, одновременно
- **hierarchical**: Один агент координирует работу остальных
- **collaborative**: Агенты сотрудничают и делятся результатами (по умолчанию)
- **pipeline**: Агенты работают в режиме конвейера

### Статусы команды

- **draft**: Черновик (по умолчанию)
- **active**: Активная команда
- **paused**: Приостановлена
- **deprecated**: Устарела

## Связь с агентами

Связь между командами и агентами реализована через промежуточную таблицу `agent_team_associations`:

- **team_id**: UUID - ID команды
- **agent_id**: UUID - ID агента
- **role**: String(100) - роль агента в команде
- **assigned_at**: DateTime - дата назначения
- **is_lead**: Boolean - является ли агент лидером команды

## Использование

### Создание команды

```python
from app.models.agent_team import AgentTeam, CoordinationStrategy, TeamStatus

team = AgentTeam(
    name="Development Team",
    description="Team for software development tasks",
    coordination_strategy=CoordinationStrategy.COLLABORATIVE.value,
    roles={
        "developer": "Writes and implements code",
        "reviewer": "Reviews code and provides feedback",
        "tester": "Tests the implementation"
    },
    status=TeamStatus.ACTIVE.value
)

db.add(team)
db.commit()
```

### Добавление агентов в команду

```python
from app.models.agent_team import agent_team_association

# Добавление агента с ролью
association = agent_team_association.insert().values(
    team_id=team.id,
    agent_id=agent.id,
    role="developer",
    is_lead=False
)
db.execute(association)
db.commit()
```

### Получение агентов команды

```python
# Получить всех агентов команды
agents = team.agents.all()

# Получить агентов по роли (требует реализации в сервисе)
developers = team.get_agents_by_role("developer")
```

## Миграция базы данных

Миграция `027_add_agent_teams.py` создает:

1. Таблицу `agent_teams` с полями команды
2. Таблицу `agent_team_associations` для связи many-to-many
3. Индексы для оптимизации запросов

Применить миграцию:

```bash
alembic upgrade head
```

## Тестирование

Тесты модели находятся в `backend/tests/test_agent_team_model.py`:

- `test_agent_team_creation` - создание команды
- `test_agent_team_unique_name` - уникальность имени
- `test_agent_team_defaults` - значения по умолчанию
- `test_agent_team_to_dict` - преобразование в словарь
- `test_agent_team_coordination_strategies` - все стратегии координации
- `test_agent_team_status_enum` - все статусы команды

Запуск тестов:

```bash
pytest backend/tests/test_agent_team_model.py -v
```

## AgentTeamService

### Основные методы

#### Создание и управление командами

```python
from app.services.agent_team_service import AgentTeamService

service = AgentTeamService(db)

# Создать команду
team = service.create_team(
    name="Development Team",
    description="Team for software development",
    coordination_strategy=CoordinationStrategy.COLLABORATIVE.value,
    roles={"developer": "Writes code", "reviewer": "Reviews code"}
)

# Получить команду
team = service.get_team(team_id)

# Обновить команду
service.update_team(
    team_id,
    description="Updated description",
    status=TeamStatus.ACTIVE.value
)

# Удалить команду
service.delete_team(team_id)
```

#### Управление составом команды

```python
# Добавить агента в команду
service.add_agent_to_team(
    team_id=team.id,
    agent_id=agent.id,
    role="developer",
    is_lead=False
)

# Удалить агента из команды
service.remove_agent_from_team(team_id, agent_id)

# Обновить роль агента
service.update_agent_role(
    team_id,
    agent_id,
    role="senior_developer",
    is_lead=True
)

# Установить лидера команды
service.set_team_lead(team_id, agent_id)
```

#### Получение информации

```python
# Получить всех агентов команды
agents = service.get_team_agents(team_id)

# Получить агентов по роли
developers = service.get_agents_by_role(team_id, "developer")

# Получить лидера команды
lead = service.get_team_lead(team_id)
```

#### Управление статусом

```python
# Активировать команду
service.activate_team(team_id)

# Приостановить команду
service.pause_team(team_id)
```

## AgentTeamCoordination

### Координация через A2A протокол

`AgentTeamCoordination` обеспечивает координацию работы команды агентов через A2A (Agent-to-Agent) протокол.

#### Распределение задач

```python
from app.services.agent_team_coordination import AgentTeamCoordination

coordination = AgentTeamCoordination(db)

# Распределить задачу команде
result = await coordination.distribute_task_to_team(
    team_id=team.id,
    task_description="Выполнить анализ кода",
    task_context={"file": "main.py"},
    assign_to_role="developer"  # Опционально: назначить конкретной роли
)

# Результат содержит:
# {
#     "distributed_to": [agent_ids],
#     "strategy_used": "collaborative",
#     "messages_sent": 3,
#     "responses": [...]
# }
```

#### Стратегии координации

1. **SEQUENTIAL** - Последовательное выполнение
   - Задачи выполняются по очереди
   - Каждый агент получает результат предыдущего

2. **PARALLEL** - Параллельное выполнение
   - Все агенты работают одновременно
   - Результаты собираются независимо

3. **HIERARCHICAL** - Иерархическая координация
   - Лидер команды координирует остальных
   - Лидер получает задачу и распределяет подзадачи

4. **COLLABORATIVE** - Коллаборативная работа
   - Все агенты получают задачу
   - Результаты делятся между всеми для финальной коллаборации

5. **PIPELINE** - Конвейерная обработка
   - Каждый агент обрабатывает свою стадию
   - Результат передается следующему агенту

#### Обмен результатами

```python
# Поделиться результатом между агентами команды
result = await coordination.share_result_between_agents(
    team_id=team.id,
    from_agent_id=agent1.id,
    result={"analysis": "Code is clean"},
    target_agents=[agent2.id, agent3.id]  # Опционально: конкретные агенты
)
```

## Следующие шаги

- Интеграция с `PlanningService` для назначения команд задачам

