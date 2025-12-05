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

## Следующие шаги

1. Создание модели BenchmarkResult для хранения результатов выполнения
2. Реализация BenchmarkService для выполнения тестов
3. Создание API endpoints для управления benchmark задачами
4. Реализация системы оценки результатов
5. Создание UI для тестирования моделей

