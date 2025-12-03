# ✅ Настройка логирования и поддержка Markdown

## 1. Система логирования

### Создан модуль `backend/app/core/logging_config.py`

**Возможности:**
- Централизованная настройка логирования
- Управление уровнями логирования для отдельных модулей
- Отключение SQLAlchemy query logging по умолчанию
- Отключение Uvicorn access logs по умолчанию

### Настройки в `.env`

```env
# Общий уровень логирования
LOG_LEVEL=INFO

# Включить логирование SQL запросов (по умолчанию выключено)
LOG_SQLALCHEMY=false

# Включить access логи Uvicorn (по умолчанию выключено)
LOG_UVICORN_ACCESS=false

# Уровни логирования для отдельных модулей (JSON)
LOG_MODULE_LEVELS={"app.api.routes.chat": "DEBUG", "app.core.ollama_client": "DEBUG"}
```

### Использование в коде

```python
from app.core.logging_config import LoggingConfig

# Получить logger для модуля
logger = LoggingConfig.get_logger(__name__)

# Использовать
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")

# Изменить уровень логирования для модуля
LoggingConfig.set_module_level("app.api.routes.chat", "DEBUG")
```

### Модули с настройками по умолчанию

- `sqlalchemy.engine` → WARNING (SQL запросы отключены)
- `sqlalchemy.pool` → WARNING
- `sqlalchemy.dialects` → WARNING
- `uvicorn.access` → WARNING (access logs отключены)
- `uvicorn.error` → INFO
- `app` → из `LOG_LEVEL`
- `root` → из `LOG_LEVEL`

## 2. Поддержка Markdown и подсветки синтаксиса

### Добавлены библиотеки

**Frontend:**
- `marked.js` - парсер Markdown
- `highlight.js` - подсветка синтаксиса кода

**Поддерживаемые языки:**
- JSON
- Python
- JavaScript
- Bash
- SQL

### Стили Markdown

Добавлены стили для:
- Заголовки (h1, h2, h3)
- Списки (ul, ol)
- Код (inline и блоки)
- Блоки кода с подсветкой синтаксиса
- Цитаты (blockquote)
- Таблицы
- Ссылки
- Горизонтальные разделители

### Автоматическая обработка

1. **При получении ответа от сервера:**
   - Markdown автоматически парсится в HTML
   - Блоки кода автоматически подсвечиваются

2. **В `message_fragment.html`:**
   - Добавлен атрибут `data-markdown` для автоматической обработки
   - Скрипт обрабатывает markdown при загрузке

3. **В `main.html`:**
   - Обработка markdown при добавлении новых сообщений через JavaScript

### Примеры поддерживаемого контента

**Markdown:**
```markdown
# Заголовок
## Подзаголовок

- Список
- Элементы

**Жирный текст** и *курсив*
```

**Код:**
````markdown
```python
def hello():
    print("Hello, World!")
```
````

**JSON:**
````markdown
```json
{
  "key": "value",
  "number": 42
}
```
````

## 3. Результат

### Логирование
- ✅ SQLAlchemy query logging отключен по умолчанию
- ✅ Uvicorn access logs отключены по умолчанию
- ✅ Централизованная система управления логированием
- ✅ Возможность настройки уровней для отдельных модулей

### Markdown и код
- ✅ Автоматический парсинг Markdown
- ✅ Подсветка синтаксиса для кода
- ✅ Поддержка JSON, Python, JavaScript, Bash, SQL
- ✅ Красивое отображение таблиц, списков, цитат
- ✅ Стили GitHub-подобного markdown

## 4. Следующие шаги

1. **Перезапустите сервер** - логирование настроится автоматически
2. **Обновите страницу** - markdown библиотеки загрузятся
3. **Отправьте сообщение** - ответ будет отформатирован с markdown и подсветкой синтаксиса

## 5. Настройка логирования в будущем

Для включения детального логирования добавьте в `.env`:

```env
LOG_LEVEL=DEBUG
LOG_SQLALCHEMY=true
LOG_UVICORN_ACCESS=true
LOG_MODULE_LEVELS={"app.api.routes.chat": "DEBUG", "app.core.ollama_client": "DEBUG"}
```

Для отключения всех логов (кроме ошибок):

```env
LOG_LEVEL=WARNING
LOG_SQLALCHEMY=false
LOG_UVICORN_ACCESS=false
```

