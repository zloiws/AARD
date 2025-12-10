# Реализация мониторинга старения агентов

## ✅ Выполнено

### Сервис AgentAgingMonitor
**Файл:** `backend/app/services/agent_aging_monitor.py`

**Функциональность:**

#### 1. Проверка старения агента (`check_agent_aging`)
Анализирует агента на признаки старения/деградации:
- **Деградация производительности:**
  - Низкий success_rate (<70%)
  - Высокий error_rate (>30%)
  - Медленное выполнение (>60s среднее время)
  
- **Деградация версии:**
  - Сравнение с предыдущими версиями через ArtifactVersionService
  - Обнаружение деградации метрик (>15%)
  
- **Паттерны использования:**
  - Долгое неиспользование (>90 дней)
  - Агент никогда не использовался (>30 дней с создания)
  - Старый агент (>365 дней)
  
- **Статус здоровья:**
  - UNHEALTHY или DEGRADED статус
  - Устаревшая проверка здоровья (>7 дней)

#### 2. Создание задач на обновление (`create_update_task`)
- Создает задачу для обновления агента при обнаружении деградации
- Проверяет, не существует ли уже такая задача
- Приоритет задачи зависит от серьезности (severity)
- Сохраняет анализ старения в контексте задачи

#### 3. Мониторинг всех агентов (`monitor_all_agents`)
- Проверяет все активные агенты
- Создает задачи для агентов с деградацией выше порога
- Возвращает статистику:
  - Общее количество агентов
  - Количество стареющих агентов
  - Количество созданных задач
  - Распределение по серьезности

### Уровни серьезности (Severity)

- **none** - Проблем не обнаружено
- **low** - Незначительные проблемы (старый агент, низкое использование)
- **medium** - Средние проблемы (снижение производительности, устаревшая проверка здоровья)
- **high** - Серьезные проблемы (низкий success_rate, высокая ошибка, деградация версии)
- **critical** - Критические проблемы (UNHEALTHY статус)

### Рекомендации

Сервис автоматически генерирует рекомендации на основе обнаруженных проблем:
- Обновление промпта для улучшения success_rate
- Исправление паттернов ошибок
- Оптимизация выполнения
- Откат к предыдущей версии
- Депрекация неиспользуемых агентов
- Проверка здоровья и конфигурации

## Использование

### Проверка одного агента

```python
from app.services.agent_aging_monitor import AgentAgingMonitor

monitor = AgentAgingMonitor(db)

# Проверить агента
analysis = monitor.check_agent_aging(agent_id)

if analysis["is_aging"]:
    print(f"Agent is aging: {analysis['severity']}")
    print(f"Issues: {len(analysis['issues'])}")
    print(f"Recommendations: {analysis['recommendations']}")
    
    # Создать задачу на обновление
    task = monitor.create_update_task(agent_id, analysis)
```

### Мониторинг всех агентов

```python
# Проверить все активные агенты
results = monitor.monitor_all_agents(min_severity="medium")

print(f"Total agents: {results['total_agents']}")
print(f"Aging agents: {len(results['aging_agents'])}")
print(f"Tasks created: {results['tasks_created']}")
print(f"Severity distribution: {results['severity_distribution']}")
```

### Интеграция в периодический мониторинг

Рекомендуется запускать мониторинг периодически (например, раз в день):

```python
# В scheduled task или cron job
from app.services.agent_aging_monitor import AgentAgingMonitor

monitor = AgentAgingMonitor(db)
results = monitor.monitor_all_agents(min_severity="high")

# Логировать результаты
logger.info(f"Agent aging check: {results['tasks_created']} update tasks created")
```

## Метрики, отслеживаемые в модели Agent

- `total_tasks_executed` - Общее количество выполненных задач
- `successful_tasks` - Количество успешных задач
- `failed_tasks` - Количество неудачных задач
- `average_execution_time` - Среднее время выполнения
- `success_rate` - Процент успешных задач
- `last_used_at` - Время последнего использования
- `health_status` - Статус здоровья (healthy, degraded, unhealthy)
- `last_health_check` - Время последней проверки здоровья

## Следующие шаги

1. ⏳ Интеграция в периодический планировщик (scheduler)
2. ⏳ API endpoints для ручного запуска мониторинга
3. ⏳ Уведомления при обнаружении критических проблем
4. ⏳ Интеграция с системой самоулучшения агентов
5. ⏳ Визуализация метрик старения в UI

