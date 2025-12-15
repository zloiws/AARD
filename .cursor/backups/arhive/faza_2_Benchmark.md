ФАЗА 2: Benchmark Suite для моделей
Цель: Создать систему для тестирования и сравнения моделей по разным типам задач.

Этап 2.1: Структура Benchmark Suite
Шаг 2.1.1: Создать модель BenchmarkTask
Файлы:

backend/app/models/benchmark_task.py (новый)
Миграция 021_add_benchmark_system.py
Задача:

Модель для хранения тестовых задач
Поля: task_type, task_description, expected_output, evaluation_criteria, category
Связь с результатами выполнения
Тесты:

Частный: backend/tests/test_benchmark_task_model.py
Общий: Интеграция с БД
Документация: Создать docs/guides/BENCHMARK_SYSTEM.md

Коммит: feat(phase2.1.1): модель BenchmarkTask

Шаг 2.1.2: Создать модель BenchmarkResult
Файлы:

backend/app/models/benchmark_result.py (новый)
Миграция (обновить или добавить в 021)
Задача:

Модель для хранения результатов выполнения benchmark
Поля: benchmark_task_id, model_id, server_id, execution_time, output, score, metrics, passed
Связь с BenchmarkTask и OllamaModel
Тесты:

Частный: backend/tests/test_benchmark_result_model.py
Общий: Интеграция
Документация: Обновить документацию

Коммит: feat(phase2.1.2): модель BenchmarkResult

Шаг 2.1.3: Создать начальный набор benchmark задач
Файлы:

backend/app/services/benchmark_service.py (новый)
backend/data/benchmarks/ (новая директория)
JSON/YAML файлы с benchmark задачами
Задача:

Создать набор тестовых задач для каждого типа:
code_generation - 10 задач
code_analysis - 5 задач
reasoning - 10 задач
planning - 10 задач
general_chat - 5 задач
Скрипт для импорта задач в БД
Тесты:

Частный: Тесты загрузки benchmark задач
Общий: Проверка структуры задач
Документация: Обновить документацию

Коммит: feat(phase2.1.3): начальный набор benchmark задач

Тест этапа 2.1: backend/tests/integration/test_benchmark_models.py

Документация этапа: Обновить docs/guides/BENCHMARK_SYSTEM.md

Коммит этапа: feat(phase2.1): структура Benchmark Suite

---

Этап 2.2: BenchmarkService - выполнение тестов
Шаг 2.2.1: Реализовать BenchmarkService для выполнения тестов
Файлы:

backend/app/services/benchmark_service.py
Методы: run_benchmark(), run_suite(), compare_models()
Задача:

Выполнение одной benchmark задачи с указанной моделью
Запуск полного suite для модели
Сравнение результатов разных моделей
Оценка результатов через evaluation_criteria
Тесты:

Частный: backend/tests/test_benchmark_service.py
Общий: backend/tests/integration/test_benchmark_execution.py
Документация: Обновить docs/guides/BENCHMARK_SYSTEM.md

Коммит: feat(phase2.2.1): BenchmarkService для выполнения тестов

Шаг 2.2.2: Реализовать систему оценки результатов
Файлы:

backend/app/services/benchmark_service.py
Методы: evaluate_result(), calculate_score()
Задача:

Автоматическая оценка результатов через LLM
Сравнение с expected_output
Расчет метрик: точность, релевантность, скорость
Сохранение оценок в BenchmarkResult
Тесты:

Частный: backend/tests/test_benchmark_evaluation.py
Общий: Полный цикл выполнения и оценки
Документация: Обновить документацию

Коммит: feat(phase2.2.2): система оценки результатов benchmark

Шаг 2.2.3: Создать API endpoints для benchmark
Файлы:

backend/app/api/routes/benchmarks.py (новый)
frontend/templates/benchmarks/run.html (новый)
Задача:

GET /api/benchmarks/tasks/ - список benchmark задач
POST /api/benchmarks/run/ - запуск benchmark для модели
GET /api/benchmarks/results/ - результаты тестов
GET /api/benchmarks/comparison/ - сравнение моделей
Тесты:

Частный: backend/tests/test_benchmark_api.py
Общий: backend/tests/integration/test_benchmark_api_full.py
Документация: Обновить API документацию

Коммит: feat(phase2.2.3): API endpoints для benchmark

Тест этапа 2.2: backend/tests/integration/test_benchmark_service_complete.py

Документация этапа: Обновить документацию

Коммит этапа: feat(phase2.2): выполнение benchmark тестов

---

Этап 2.3: UI для тестирования моделей
Шаг 2.3.1: Создать страницу выбора benchmark задач
Файлы:

frontend/templates/benchmarks/index.html (новый)
backend/app/api/routes/pages.py - добавить роут
Задача:

Список доступных benchmark задач с фильтрацией по типу
Выбор моделей для тестирования
Кнопка запуска тестов
Тесты:

Частный: Мануальное тестирование UI
Общий: E2E тест выбора и запуска
Документация: Обновить docs/WEB_INTERFACE.md

Коммит: feat(phase2.3.1): страница выбора benchmark задач

Шаг 2.3.2: Создать страницу результатов тестирования
Файлы:

frontend/templates/benchmarks/results.html (новый)
Реалтайм обновление через WebSocket
Задача:

Отображение результатов выполнения тестов в реальном времени
Таблица с метриками: время, точность, статус
Графики сравнения моделей
Тесты:

Частный: Мануальное тестирование
Общий: E2E тест просмотра результатов
Документация: Обновить документацию

Коммит: feat(phase2.3.2): страница результатов benchmark

Шаг 2.3.3: Создать страницу сравнения моделей
Файлы:

frontend/templates/benchmarks/comparison.html (новый)
Задача:

Сравнительная таблица моделей по разным типам задач
Визуализация метрик (графики, диаграммы)
Рекомендации по выбору модели для задачи
Тесты:

Частный: Мануальное тестирование
Общий: E2E тест сравнения
Документация: Обновить документацию

Коммит: feat(phase2.3.3): страница сравнения моделей

Тест этапа 2.3: E2E тест полного цикла benchmark

Документация этапа: Обновить docs/WEB_INTERFACE.md

Коммит этапа: feat(phase2.3): UI для тестирования моделей

---

Тест фазы 2: backend/tests/integration/test_benchmark_system_complete.py

Документация фазы: Создать docs/guides/BENCHMARK_SYSTEM.md (полный обзор)

Коммит фазы: feat(phase2): Benchmark Suite для моделей

Правила выполнения плана
После каждого ШАГА:
Частный тест: Тест конкретной функции/метода
Общий тест: Интеграционный или комплексный тест
Документация: Обновить соответствующую документацию
Коммит: Создать коммит с описанием изменений
После каждого ЭТАПА:
Этапный тест: Комплексный тест всего этапа
Документация этапа: Создать/обновить документацию этапа
Коммит этапа: Коммит с префиксом feat(phaseX.Y):
После каждой ФАЗЫ:
Фазный тест: Полный тест всей фазы
Документация фазы: Полная документация фазы
Коммит фазы: Коммит с префиксом feat(phaseX):
Согласование между элементами:
Каждый шаг должен быть независим и тестируем
Зависимости между шагами явно указаны
Тесты каждого уровня проверяют согласованность с предыдущими уровнями
Документация обновляется на каждом уровне
Поддерживается целостность архитектуры проекта