# Инструкция по установке и запуску AARD

## Шаг 1: Создание виртуального окружения

**Рекомендуется использовать виртуальное окружение для изоляции зависимостей:**

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Или (Windows CMD)
venv\Scripts\activate.bat

# Или использовать скрипты из корня проекта
.\activate.ps1  # PowerShell
.\activate.bat  # CMD

# Linux/Mac
source venv/bin/activate
```

## Шаг 2: Установка зависимостей

```bash
cd backend
pip install -r requirements.txt
```

## Шаг 3: Настройка переменных окружения

1. Скопируйте `.env.example` в `.env` в корне проекта:
   ```bash
   cp .env.example .env
   ```

2. Отредактируйте `.env` файл и убедитесь, что все параметры корректны:
   - `POSTGRES_HOST=10.39.0.101`
   - `POSTGRES_DB=aard`
   - `POSTGRES_USER=postgres`
   - `POSTGRES_PASSWORD=Cdthrf12`
   - `POSTGRES_PORT=5432`

3. Сгенерируйте `SECRET_KEY`:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Замените `<generate_secret_key_here>` в `.env` на сгенерированный ключ.

## Шаг 4: Проверка подключения к базе данных

Убедитесь, что PostgreSQL доступен:

```bash
# Проверка подключения
psql -h 10.39.0.101 -p 5432 -U postgres -d aard
```

Если подключение успешно, установите расширения:

```sql
\c aard
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
\q
```

## Шаг 5: Применение миграций

```bash
cd backend
alembic upgrade head
```

Это создаст таблицы `tasks`, `artifacts` и `artifact_dependencies` в базе данных.

## Шаг 6: Запуск приложения

**Убедитесь, что виртуальное окружение активировано!**

```bash
# Из корня проекта (рекомендуется)
python backend/run.py

# Или через uvicorn напрямую
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

Приложение будет доступно по адресу: http://localhost:8000

## Проверка работы

1. Проверьте корневой endpoint:
   ```bash
   curl http://localhost:8000/
   ```

2. Проверьте health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

3. Откройте документацию API:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Устранение проблем

### Ошибка подключения к БД
- Проверьте, что PostgreSQL запущен
- Убедитесь, что хост и порт корректны
- Проверьте имя базы данных и учетные данные

### Ошибка импорта модулей
- Убедитесь, что вы находитесь в директории `backend`
- Проверьте, что все зависимости установлены
- Убедитесь, что Python видит модуль `app` (добавьте путь в PYTHONPATH если нужно)

### Ошибки миграций
- Убедитесь, что расширение `vector` установлено в PostgreSQL
- Проверьте, что у пользователя БД есть права на создание таблиц
- Если нужно, откатите миграции: `alembic downgrade -1`

## Следующие шаги

После успешного запуска базового приложения можно переходить к:
1. Интеграции с Ollama (Неделя 3-4)
2. Созданию чат API (Неделя 5-6)
3. Веб-интерфейсу (Неделя 5-6)

