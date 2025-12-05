# AARD - Autonomous Agentic Recursive Development

Автономная агентная платформа развития (AARD) - система для создания и управления автономными ИИ-агентами, работающая в полностью локальном окружении.

## Описание

AARD начинает как "голый мозг" (LLM через Ollama) с веб-интерфейсом и развивается под руководством человека, создавая себе "тело и нервную систему" (агентов, инструменты, оркестрацию).

Система поддерживает:
- **Планирование задач** через LLM с автоматическим разбиением на подзадачи
- **Выполнение планов** с поддержкой workflow и checkpoint'ов
- **Human-in-the-Loop** с адаптивным утверждением и интерактивным выполнением
- **Самообучение** через мета-обучение, обратную связь и метрики планирования
- **Безопасность** через sandbox для выполнения кода и валидацию
- **Наблюдаемость** через логирование, метрики и трассировку

## Текущая инфраструктура

- **PostgreSQL:** 10.39.0.101:5432 (база: aard, пользователь: postgres)
- **Ollama Instance 1:** http://10.39.0.101:11434/v1 (deepseek-r1-abliterated:8b)
- **Ollama Instance 2:** http://10.39.0.6:11434/v1 (qwen3-coder:30b-a3b-q4_K_M)

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните параметры
2. Установите зависимости: `pip install -r backend/requirements.txt`
3. Примените миграции БД: `cd backend && alembic upgrade head`
4. Запустите приложение: `cd backend && python main.py`
5. Откройте веб-интерфейс: http://localhost:8000

## Структура проекта

```
aard/
├── backend/          # Backend (FastAPI)
│   ├── app/         # Основное приложение
│   │   ├── api/     # API routes
│   │   ├── core/    # Ядро системы (конфигурация, БД, клиенты)
│   │   ├── models/  # Модели данных
│   │   ├── services/# Бизнес-логика
│   │   ├── agents/  # Агенты
│   │   └── tools/   # Инструменты
│   ├── tests/       # Тесты
│   │   └── integration/  # Интеграционные тесты
│   ├── scripts/     # Утилитарные скрипты
│   └── alembic/     # Миграции БД
├── frontend/         # Frontend (HTMX + Jinja2)
│   └── templates/   # HTML шаблоны
├── docs/             # Документация
│   ├── guides/      # Актуальные руководства
│   ├── archive/     # Архивные документы
│   └── ТЗ AARD.md   # Техническое задание
└── .cursor/          # Планы разработки
    └── plans/        # Планы проекта
```

## Документация

Полная документация доступна в [docs/README.md](docs/README.md)

### Основные руководства

- **[Установка и настройка](docs/guides/SETUP.md)** - Первоначальная настройка системы
- **[Запуск сервера](docs/guides/START_SERVER.md)** - Как запустить приложение
- **[Логирование](docs/guides/LOGGING.md)** - Настройка и использование логирования
- **[Планирование](docs/guides/PLANNING_METRICS.md)** - Система планирования задач
- **[Агенты](docs/guides/AGENTS.md)** - Работа с агентами
- **[Инструменты](docs/guides/TOOLS.md)** - Создание и использование инструментов

### Архитектура

- **[Dual-Model Architecture](docs/guides/DUAL_MODEL_ARCHITECTURE.md)** - Архитектура с двумя моделями
- **[Task Lifecycle](docs/guides/TASK_LIFECYCLE.md)** - Жизненный цикл задач
- **[Automatic Replanning](docs/guides/AUTOMATIC_REPLANNING.md)** - Автоматическое перепланирование

### Статус реализации

- **[Статус реализации](docs/IMPLEMENTATION_STATUS.md)** - Текущий статус компонентов
- **[Консолидированный план](.cursor/plans/consolidated_master_plan.md)** - Единый план развития

## Основные компоненты

### Реализовано

- ✅ Система планирования задач (PlanningService)
- ✅ Система выполнения планов (ExecutionService)
- ✅ Workflow Events для отслеживания событий
- ✅ WebSocket API для real-time обновлений
- ✅ Model Logs интеграция
- ✅ Tracing система (OpenTelemetry)
- ✅ Adaptive Approval Service
- ✅ Interactive Execution Service
- ✅ Meta-Learning Service
- ✅ Feedback Learning Service
- ✅ Planning Metrics Service
- ✅ Code Execution Sandbox
- ✅ Memory Service
- ✅ Agent Gym для тестирования агентов

### В разработке

- ⏳ Автоматическое перепланирование при ошибках
- ⏳ Визуализация планов (дерево шагов)
- ⏳ Расширенная система безопасности (RBAC, Network Proxy)
- ⏳ Graduated Autonomy уровни

## Разработка

### Планы разработки

- **[Консолидированный план](.cursor/plans/consolidated_master_plan.md)** - Единый план развития проекта
- **[Фаза 9: Рефакторинг и документация](.cursor/plans/faza9_refatoring_and_docs.md)** - Текущая фаза

### Скрипты

- `backend/scripts/code_audit.py` - Аудит кода на дублирование
- `backend/scripts/cleanup_unused_code.py` - Очистка неиспользуемого кода
- `backend/scripts/consolidate_duplicates.py` - Консолидация дублированного функционала
- `backend/scripts/consolidate_plans.py` - Консолидация планов проекта
- `backend/scripts/reorganize_docs.py` - Реорганизация документации

## Технический долг

См. [docs/TECHNICAL_DEBT.md](docs/TECHNICAL_DEBT.md) для детального отчета о техническом долге.

## Лицензия

[Указать лицензию]

