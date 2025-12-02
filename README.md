# AARD - Autonomous Agentic Recursive Development

Автономная агентная платформа развития (AARD) - система для создания и управления автономными ИИ-агентами, работающая в полностью локальном окружении.

## Описание

AARD начинает как "голый мозг" (LLM через Ollama) с веб-интерфейсом и развивается под руководством человека, создавая себе "тело и нервную систему" (агентов, инструменты, оркестрацию).

## Текущая инфраструктура

- **PostgreSQL:** 10.39.0.101:5432 (база: aard, пользователь: postgres)
- **Ollama Instance 1:** http://10.39.0.101:11434/v1 (deepseek-r1-abliterated:8b)
- **Ollama Instance 2:** http://10.39.0.6:11434/v1 (qwen3-coder:30b-a3b-q4_K_M)

## Быстрый старт

1. Скопируйте `.env.example` в `.env` и заполните параметры
2. Установите зависимости: `pip install -r backend/requirements.txt`
3. Примените миграции БД: `cd backend && alembic upgrade head`
4. Запустите приложение: `cd backend && python main.py`

## Структура проекта

```
aard/
├── backend/          # Backend (FastAPI)
├── frontend/         # Frontend (HTMX + Jinja2)
├── docker/           # Docker конфигурации
├── config/           # Конфигурационные файлы
└── docs/             # Документация
```

## Разработка

См. `plan.plan.md` для детального плана разработки.

## Лицензия

[Указать лицензию]

