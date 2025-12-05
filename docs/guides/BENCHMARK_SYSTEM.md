# Benchmark System

## Обзор

Система Benchmark предназначена для тестирования и сравнения моделей LLM по разным типам задач. Она позволяет:

- Создавать и управлять тестовыми задачами (benchmark tasks)
- Выполнять тесты с различными моделями
- Оценивать результаты выполнения
- Сравнивать производительность моделей

## Модели данных

### BenchmarkTask

Модель для хранения тестовых задач.

**Поля:**
- `id` (UUID) - уникальный идентификатор
- `task_type` (Enum) - тип задачи:
  - `CODE_GENERATION` - генерация кода
  - `CODE_ANALYSIS` - анализ кода
  - `REASONING` - логические рассуждения
  - `PLANNING` - планирование
  - `GENERAL_CHAT` - общий чат
- `category` (String) - категория задачи (например, "python", "javascript", "math")
- `name` (String, unique) - уникальное имя задачи
- `task_description` (Text) - описание задачи/промпт
- `expected_output` (Text, optional) - ожидаемый результат
- `evaluation_criteria` (JSONB) - критерии оценки в формате JSON
- `difficulty` (String, optional) - сложность: "easy", "medium", "hard"
- `tags` (JSONB) - теги для фильтрации
- `task_metadata` (JSONB) - дополнительные метаданные
- `created_at`, `updated_at` (DateTime) - временные метки

**Пример использования:**

```python
from app.models.benchmark_task import BenchmarkTask, BenchmarkTaskType

task = BenchmarkTask(
    task_type=BenchmarkTaskType.CODE_GENERATION,
    category="python",
    name="factorial_function",
    task_description="Write a function to calculate factorial",
    expected_output="def factorial(n): ...",
    evaluation_criteria={"accuracy": 1.0, "code_quality": 0.8},
    difficulty="medium",
    tags=["python", "recursion"]
)
```

## API Endpoints

(Будет добавлено в следующих этапах)

## Миграции

Миграция `021_add_benchmark_system.py` создает таблицу `benchmark_tasks` со всеми необходимыми полями и индексами.

## Тестирование

### Unit тесты

- `tests/test_benchmark_task_model.py` - тесты модели BenchmarkTask

### Integration тесты

- `tests/integration/test_benchmark_models.py` - интеграционные тесты с базой данных

### BenchmarkResult

Модель для хранения результатов выполнения benchmark тестов.

**Поля:**
- `id` (UUID) - уникальный идентификатор
- `benchmark_task_id` (UUID, FK) - ссылка на задачу
- `model_id` (UUID, FK, optional) - ссылка на модель
- `server_id` (UUID, FK, optional) - ссылка на сервер
- `execution_time` (Float) - время выполнения в секундах
- `output` (Text) - вывод модели
- `score` (Float) - общая оценка (0.0-1.0)
- `metrics` (JSONB) - детальные метрики
- `passed` (Boolean) - прошел ли тест
- `error_message` (Text, optional) - сообщение об ошибке
- `execution_metadata` (JSONB) - дополнительные метаданные
- `created_at` (DateTime) - время создания

## BenchmarkService

Сервис для управления benchmark задачами.

**Основные методы:**

**Управление задачами:**
- `load_tasks_from_file(file_path)` - загрузка задач из JSON файла
- `import_task(task_data)` - импорт одной задачи в БД
- `import_tasks_from_directory(directory)` - импорт всех задач из директории
- `get_task_by_name(name)` - получение задачи по имени
- `list_tasks(task_type, category, difficulty, limit)` - список задач с фильтрами
- `get_task_count_by_type()` - количество задач по типам

**Выполнение тестов:**
- `run_benchmark(task_id, model_id, model_name, server_id, server_url, timeout)` - выполнение одной benchmark задачи
- `run_suite(task_type, model_id, model_name, server_id, server_url, limit, timeout)` - запуск полного suite для модели
- `compare_models(model_ids, task_type, limit)` - сравнение результатов разных моделей

**Оценка результатов:**
- `evaluate_result(result_id, use_llm)` - оценка результата выполнения
  * Автоматическая оценка через LLM (если use_llm=True)
  * Простое сравнение с expected_output (если use_llm=False)
  * Расчет метрик: точность, релевантность
  * Сохранение score и metrics в BenchmarkResult
- `calculate_score(result, criteria)` - расчет общего score из метрик
  * Поддержка весов для разных метрик
  * Простое усреднение при отсутствии весов
- `_llm_evaluate()` - внутренний метод для LLM-оценки
- `_simple_evaluate()` - внутренний метод для простой оценки

## Начальный набор задач

Создан начальный набор из 40 benchmark задач:

- **code_generation**: 10 задач (Python функции: factorial, reverse_string, binary_search, и др.)
- **code_analysis**: 5 задач (анализ сложности, поиск багов, оптимизация, безопасность)
- **reasoning**: 10 задач (математика, логика, паттерны, причинно-следственные связи)
- **planning**: 10 задач (планирование поездок, проектов, обучения, бюджета)
- **general_chat**: 5 задач (объяснения, творчество, советы, сравнения, резюме)

Задачи хранятся в `backend/data/benchmarks/` в формате JSON:
- `code_generation.json`
- `code_analysis.json`
- `reasoning.json`
- `planning.json`
- `general_chat.json`

### Импорт задач

Для импорта задач в базу данных используйте скрипт:

```bash
python backend/scripts/import_benchmark_tasks.py
```

Скрипт автоматически:
- Загружает все JSON файлы из `backend/data/benchmarks/`
- Импортирует задачи в базу данных
- Пропускает уже существующие задачи
- Выводит статистику импорта

## Следующие шаги

1. ✅ Создание модели BenchmarkResult - завершено
2. ✅ Реализация BenchmarkService для управления задачами - завершено
3. Реализация BenchmarkService для выполнения тестов
4. Создание API endpoints для управления benchmark задачами
5. Реализация системы оценки результатов
6. Создание UI для тестирования моделей

