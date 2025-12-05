План реализации критических компонентов AARD
Цель: Реализовать все критически важные недостающие компоненты, выявленные при анализе существующих платформ.

Принципы:

Каждый шаг завершается тестами, документацией и коммитом
Поддержка целостности архитектуры проекта
Очистка и реорганизация кода при необходимости
Тестирование от простого к сложному для каждого модуля
---

ФАЗА 1: Система управления промптами (базовая версия)
Цель: Создать базовую систему управления промптами с версионированием и метриками.

Зависимости: Модель Prompt уже существует, нужен сервис управления.

Этап 1.1: PromptService - базовое управление
Шаг 1.1.1: Создать PromptService с базовыми методами
Файлы:

backend/app/services/prompt_service.py (новый)
backend/tests/test_prompt_service.py (новый)
Задача:

Создать PromptService с методами:
create_prompt() - создание нового промпта
get_prompt() - получение промпта по ID
get_active_prompt() - получение активного промпта по имени/типу
list_prompts() - список промптов с фильтрацией
update_prompt() - обновление промпта
create_version() - создание новой версии промпта
deprecate_prompt() - отключение промпта
Тесты:

Частный: backend/tests/test_prompt_service.py - тесты всех методов
Общий: backend/tests/integration/test_prompt_service_integration.py - интеграция с БД
Документация: Создать docs/guides/PROMPT_MANAGEMENT.md

Коммит: feat(phase1.1.1): базовая система управления промптами

Шаг 1.1.2: Интегрировать PromptService в PlanningService
Файлы:

backend/app/services/planning_service.py
Обновить методы _analyze_task() и _decompose_task() для использования промптов из БД
Задача:

Заменить жестко закодированные промпты на загрузку из БД через PromptService
Поддержка fallback на хардкод если промпт не найден
Сохранение используемых промптов в Digital Twin context
Тесты:

Частный: Обновить существующие тесты PlanningService
Общий: backend/tests/integration/test_planning_with_prompts.py - тест планирования с промптами из БД
Документация: Обновить docs/guides/PROMPT_MANAGEMENT.md

Коммит: feat(phase1.1.2): интеграция PromptService в PlanningService

Шаг 1.1.3: Создать API endpoints для управления промптами
Файлы:

backend/app/api/routes/prompts.py (новый или обновить существующий)
frontend/templates/prompts/list.html (новый)
Задача:

GET /api/prompts/ - список промптов
GET /api/prompts/{prompt_id} - детали промпта
POST /api/prompts/ - создание промпта
PUT /api/prompts/{prompt_id} - обновление
POST /api/prompts/{prompt_id}/version - создание версии
POST /api/prompts/{prompt_id}/deprecate - отключение
Тесты:

Частный: backend/tests/test_prompt_api.py
Общий: backend/tests/integration/test_prompt_api_full.py
Документация: Обновить API документацию

Коммит: feat(phase1.1.3): API endpoints для управления промптами

Тест этапа 1.1: backend/tests/integration/test_prompt_system_basic.py

Документация этапа: Обновить docs/guides/PROMPT_MANAGEMENT.md

Коммит этапа: feat(phase1.1): базовая система управления промптами

---

Этап 1.2: Метрики производительности промптов
Шаг 1.2.1: Добавить сбор метрик использования промптов
Файлы:

backend/app/services/prompt_service.py
Обновить PromptService для отслеживания использования
Задача:

При использовании промпта увеличивать usage_count
Сохранять время выполнения (для расчета avg_execution_time)
Интегрировать в PlanningService для автоматического сбора метрик
Тесты:

Частный: backend/tests/test_prompt_metrics.py
Общий: Интеграция в тесты PlanningService
Документация: Обновить docs/guides/PROMPT_MANAGEMENT.md

Коммит: feat(phase1.2.1): сбор метрик использования промптов

Шаг 1.2.2: Реализовать расчет success_rate для промптов
Файлы:

backend/app/services/prompt_service.py
Интеграция с PlanningService и ExecutionService
Задача:

Отслеживать успешность выполнения задач с каждым промптом
Автоматически обновлять success_rate на основе результатов выполнения
Учитывать результаты утверждения планов
Тесты:

Частный: backend/tests/test_prompt_success_rate.py
Общий: backend/tests/integration/test_prompt_metrics_full.py
Документация: Обновить документацию

Коммит: feat(phase1.2.2): расчет success_rate для промптов

Шаг 1.2.3: Создать API для просмотра метрик промптов
Файлы:

backend/app/api/routes/prompts.py
frontend/templates/prompts/metrics.html (новый)
Задача:

GET /api/prompts/{prompt_id}/metrics - метрики промпта
GET /api/prompts/metrics/comparison - сравнение метрик разных версий
Тесты:

Частный: Тесты API endpoints
Общий: E2E тест с UI
Документация: Обновить API документацию

Коммит: feat(phase1.2.3): API для метрик промптов

Тест этапа 1.2: backend/tests/integration/test_prompt_metrics_complete.py

Документация этапа: Обновить документацию

Коммит этапа: feat(phase1.2): метрики производительности промптов

---

Этап 1.3: Рефлексия и улучшение промптов
Шаг 1.3.1: Интегрировать ReflectionService для анализа промптов
Файлы:

backend/app/services/prompt_service.py
Интеграция с ReflectionService
Задача:

После использования промпта анализировать результат через ReflectionService
Сохранять анализ в improvement_history
Определять успешные и неуспешные паттерны использования
Тесты:

Частный: backend/tests/test_prompt_reflection.py
Общий: Интеграция с ReflectionService
Документация: Создать docs/guides/PROMPT_IMPROVEMENT.md

Коммит: feat(phase1.3.1): рефлексия промптов через ReflectionService

Шаг 1.3.2: Реализовать автоматические рекомендации по улучшению
Файлы:

backend/app/services/prompt_service.py
Новый метод suggest_improvements()
Задача:

Анализировать метрики и историю улучшений
Генерировать рекомендации по улучшению промпта
Использовать LLM для предложения улучшений на основе метрик
Тесты:

Частный: backend/tests/test_prompt_improvement_suggestions.py
Общий: Интеграция с PlanningService
Документация: Обновить docs/guides/PROMPT_IMPROVEMENT.md

Коммит: feat(phase1.3.2): автоматические рекомендации по улучшению промптов

Шаг 1.3.3: Создать механизм автоматического создания улучшенных версий
Файлы:

backend/app/services/prompt_service.py
Метод create_improved_version()
Задача:

На основе рекомендаций автоматически создавать новую версию промпта
Создавать версию со статусом TESTING
Автоматически запускать A/B тестирование (в следующем этапе)
Тесты:

Частный: backend/tests/test_prompt_version_creation.py
Общий: Полный цикл улучшения
Документация: Обновить документацию

Коммит: feat(phase1.3.3): автоматическое создание улучшенных версий

Тест этапа 1.3: backend/tests/integration/test_prompt_improvement_cycle.py

Документация этапа: Создать docs/guides/PROMPT_IMPROVEMENT.md

Коммит этапа: feat(phase1.3): рефлексия и улучшение промптов

---

Тест фазы 1: backend/tests/integration/test_prompt_management_system.py

Документация фазы: Создать docs/guides/PROMPT_SYSTEM.md (общий обзор)

Коммит фазы: feat(phase1): система управления промптами (базовая версия)

---

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

---

ФАЗА 3: Саморефлексия проекта
Цель: Создать систему самоанализа проекта на всех уровнях.

Этап 3.1: Система метрик проекта
Шаг 3.1.1: Создать ProjectMetricsService
Файлы:

backend/app/services/project_metrics_service.py (новый)
Модель ProjectMetric (новый)
Задача:

Сбор метрик на уровне проекта:
Общая производительность системы
Успешность выполнения задач
Среднее время выполнения
Распределение по типам задач
Тренды во времени
Тесты:

Частный: backend/tests/test_project_metrics_service.py
Общий: Интеграция с существующими сервисами
Документация: Создать docs/guides/PROJECT_REFLECTION.md

Коммит: feat(phase3.1.1): ProjectMetricsService

Шаг 3.1.2: Реализовать сбор метрик в реальном времени
Файлы:

Интеграция в PlanningService, ExecutionService, PromptService
Задача:

Автоматический сбор метрик при выполнении операций
Хранение метрик в БД
Агрегация метрик по периодам (час, день, неделя)
Тесты:

Частный: Тесты сбора метрик
Общий: Интеграция с workflow
Документация: Обновить документацию

Коммит: feat(phase3.1.2): сбор метрик в реальном времени

Шаг 3.1.3: Создать API для метрик проекта
Файлы:

backend/app/api/routes/project_metrics.py (новый)
Задача:

GET /api/metrics/project/overview - обзор метрик
GET /api/metrics/project/trends - тренды метрик
GET /api/metrics/project/comparison - сравнение периодов
Тесты:

Частный: backend/tests/test_project_metrics_api.py
Общий: Интеграция
Документация: Обновить API документацию

Коммит: feat(phase3.1.3): API для метрик проекта

Тест этапа 3.1: backend/tests/integration/test_project_metrics.py

Документация этапа: Обновить docs/guides/PROJECT_REFLECTION.md

Коммит этапа: feat(phase3.1): система метрик проекта

---

Этап 3.2: Регулярный самоаудит
Шаг 3.2.1: Реализовать SelfAuditService
Файлы:

backend/app/services/self_audit_service.py (новый)
Задача:

Методы для самоанализа:
audit_performance() - анализ производительности
audit_quality() - анализ качества планов
audit_prompts() - анализ эффективности промптов
audit_errors() - анализ ошибок и паттернов
generate_report() - генерация отчета
Тесты:

Частный: backend/tests/test_self_audit_service.py
Общий: Полный цикл аудита
Документация: Обновить docs/guides/PROJECT_REFLECTION.md

Коммит: feat(phase3.2.1): SelfAuditService

Шаг 3.2.2: Создать планировщик регулярных аудитов
Файлы:

backend/app/services/self_audit_service.py
Интеграция с фоновыми задачами
Задача:

Планировщик для запуска аудитов по расписанию (ежедневно, еженедельно)
Автоматическая генерация отчетов
Сохранение истории аудитов
Тесты:

Частный: Тесты планировщика
Общий: Тест автоматического запуска
Документация: Обновить документацию

Коммит: feat(phase3.2.2): планировщик регулярных аудитов

Шаг 3.2.3: Реализовать анализ трендов и рекомендации
Файлы:

backend/app/services/self_audit_service.py
Использование LLM для анализа
Задача:

Анализ трендов производительности
Определение улучшений и деградаций
Генерация автоматических рекомендаций по улучшению
Использование ReflectionService для глубокого анализа
Тесты:

Частный: Тесты анализа трендов
Общий: Полный цикл анализа и рекомендаций
Документация: Обновить документацию

Коммит: feat(phase3.2.3): анализ трендов и рекомендации

Тест этапа 3.2: backend/tests/integration/test_self_audit_complete.py

Документация этапа: Обновить документацию

Коммит этапа: feat(phase3.2): регулярный самоаудит

---

Этап 3.3: Dashboard метрик проекта
Шаг 3.3.1: Создать страницу метрик проекта
Файлы:

frontend/templates/metrics/project.html (новый)
backend/app/api/routes/pages.py - добавить роут
Задача:

Dashboard с ключевыми метриками
Графики трендов
Сводная статистика
Тесты:

Частный: Мануальное тестирование
Общий: E2E тест dashboard
Документация: Обновить docs/WEB_INTERFACE.md

Коммит: feat(phase3.3.1): страница метрик проекта

Шаг 3.3.2: Интегрировать отчеты самоаудита в UI
Файлы:

frontend/templates/metrics/audit_reports.html (новый)
Задача:

Просмотр истории аудитов
Детальные отчеты с рекомендациями
Фильтрация по периоду
Тесты:

Частный: Мануальное тестирование
Общий: E2E тест просмотра отчетов
Документация: Обновить документацию

Коммит: feat(phase3.3.2): UI для отчетов самоаудита

Тест этапа 3.3: E2E тест dashboard метрик

Документация этапа: Обновить документацию

Коммит этапа: feat(phase3.3): Dashboard метрик проекта

---

Тест фазы 3: backend/tests/integration/test_project_reflection_system.py

Документация фазы: Создать docs/guides/PROJECT_REFLECTION.md (полный обзор)

Коммит фазы: feat(phase3): саморефлексия проекта

---

ФАЗА 4: Векторный поиск для памяти
Цель: Улучшить поиск в памяти через векторные embeddings.

Этап 4.1: Интеграция pgvector
Шаг 4.1.1: Добавить поддержку pgvector в БД
Файлы:

Миграция 022_add_vector_search.py
Обновить backend/app/core/database.py
Задача:

Установка расширения vector в PostgreSQL
Добавить векторные поля в AgentMemory
Создать индексы для векторного поиска
Тесты:

Частный: Тесты миграции
Общий: Проверка работы pgvector
Документация: Создать docs/guides/VECTOR_SEARCH.md

Коммит: feat(phase4.1.1): интеграция pgvector в БД

Шаг 4.1.2: Реализовать сервис генерации embeddings
Файлы:

backend/app/services/embedding_service.py (новый)
Задача:

Генерация embeddings для текста через LLM (или внешний сервис)
Кэширование embeddings
Нормализация векторов
Тесты:

Частный: backend/tests/test_embedding_service.py
Общий: Интеграция с MemoryService
Документация: Обновить документацию

Коммит: feat(phase4.1.2): сервис генерации embeddings

Шаг 4.1.3: Обновить MemoryService для векторного поиска
Файлы:

backend/app/services/memory_service.py
Метод search_memories_vector()
Задача:

Добавить векторный поиск похожих ситуаций
Комбинировать с существующим текстовым поиском
Оптимизация запросов
Тесты:

Частный: backend/tests/test_memory_vector_search.py
Общий: Интеграция с PlanningService
Документация: Обновить docs/guides/MEMORY_SYSTEM.md

Коммит: feat(phase4.1.3): векторный поиск в MemoryService

Тест этапа 4.1: backend/tests/integration/test_vector_search.py

Документация этапа: Обновить docs/guides/VECTOR_SEARCH.md

Коммит этапа: feat(phase4.1): интеграция pgvector

---

Этап 4.2: Автоматическая генерация embeddings
Шаг 4.2.1: Интегрировать генерацию embeddings при сохранении памяти
Файлы:

backend/app/services/memory_service.py
Обновить save_memory()
Задача:

Автоматически генерировать embedding при сохранении памяти
Сохранять embedding в векторное поле
Обработка ошибок генерации
Тесты:

Частный: Тесты автоматической генерации
Общий: Полный цикл сохранения и поиска
Документация: Обновить документацию

Коммит: feat(phase4.2.1): автоматическая генерация embeddings

Шаг 4.2.2: Создать скрипт миграции существующих данных
Файлы:

backend/scripts/migrate_memories_to_vectors.py (новый)
Задача:

Скрипт для генерации embeddings для существующих записей памяти
Batch обработка
Прогресс и логирование
Тесты:

Частный: Тесты скрипта миграции
Общий: Проверка миграции
Документация: Обновить документацию

Коммит: feat(phase4.2.2): скрипт миграции существующих данных

Тест этапа 4.2: Тест полной миграции

Документация этапа: Обновить документацию

Коммит этапа: feat(phase4.2): автоматическая генерация embeddings

---

Тест фазы 4: backend/tests/integration/test_vector_search_complete.py

Документация фазы: Создать docs/guides/VECTOR_SEARCH.md (полный обзор)

Коммит фазы: feat(phase4): векторный поиск для памяти

---

ФАЗА 5: Система шаблонов планов
Цель: Автоматическое извлечение и использование шаблонов успешных планов.

Этап 5.1: Извлечение шаблонов из успешных планов
Шаг 5.1.1: Реализовать PlanTemplateService
Файлы:

backend/app/services/plan_template_service.py (новый)
Модель PlanTemplate (новый)
Миграция 023_add_plan_templates.py
Задача:

Извлечение шаблонов из успешных планов
Абстракция специфичных деталей
Сохранение шаблонов с метаданными
Тесты:

Частный: backend/tests/test_plan_template_service.py
Общий: Интеграция с PlanningService
Документация: Создать docs/guides/PLAN_TEMPLATES.md

Коммит: feat(phase5.1.1): PlanTemplateService

Шаг 5.1.2: Реализовать автоматическое извлечение при завершении плана
Файлы:

Интеграция в PlanningService и ExecutionService
Задача:

При успешном завершении плана анализировать его структуру
Извлекать шаблон если план соответствует критериям (успешность, качество)
Сохранять шаблон для будущего использования
Тесты:

Частный: Тесты извлечения шаблонов
Общий: Полный цикл создания и использования шаблона
Документация: Обновить документацию

Коммит: feat(phase5.1.2): автоматическое извлечение шаблонов

Шаг 5.1.3: Реализовать поиск подходящих шаблонов
Файлы:

backend/app/services/plan_template_service.py
Метод find_matching_template()
Задача:

Поиск шаблонов по описанию задачи (семантический поиск)
Ранжирование шаблонов по релевантности
Использование векторного поиска если доступен
Тесты:

Частный: Тесты поиска шаблонов
Общий: Интеграция с PlanningService
Документация: Обновить документацию

Коммит: feat(phase5.1.3): поиск подходящих шаблонов

Тест этапа 5.1: backend/tests/integration/test_plan_template_extraction.py

Документация этапа: Обновить docs/guides/PLAN_TEMPLATES.md

Коммит этапа: feat(phase5.1): извлечение шаблонов из успешных планов

---

Этап 5.2: Использование шаблонов при планировании
Шаг 5.2.1: Интегрировать шаблоны в PlanningService
Файлы:

backend/app/services/planning_service.py
Использовать PlanTemplateService в generate_plan()
Задача:

Перед генерацией плана искать подходящие шаблоны
Использовать шаблон как основу для нового плана
Адаптировать шаблон под конкретную задачу
Тесты:

Частный: Тесты использования шаблонов
Общий: Полный цикл планирования с шаблонами
Документация: Обновить документацию

Коммит: feat(phase5.2.1): интеграция шаблонов в PlanningService

Шаг 5.2.2: Реализовать адаптацию шаблона к задаче
Файлы:

backend/app/services/plan_template_service.py
Метод adapt_template()
Задача:

Замена абстрактных частей шаблона конкретными деталями задачи
Использование LLM для адаптации
Сохранение связи с оригинальным шаблоном
Тесты:

Частный: Тесты адаптации шаблонов
Общий: Интеграция
Документация: Обновить документацию

Коммит: feat(phase5.2.2): адаптация шаблона к задаче

Шаг 5.2.3: Создать API для управления шаблонами
Файлы:

backend/app/api/routes/plan_templates.py (новый)
Задача:

GET /api/plan-templates/ - список шаблонов
GET /api/plan-templates/{template_id} - детали шаблона
POST /api/plan-templates/{template_id}/use - использование шаблона
Тесты:

Частный: backend/tests/test_plan_template_api.py
Общий: Интеграция
Документация: Обновить API документацию

Коммит: feat(phase5.2.3): API для управления шаблонами

Тест этапа 5.2: backend/tests/integration/test_plan_template_usage.py

Документация этапа: Обновить документацию

Коммит этапа: feat(phase5.2): использование шаблонов при планировании

---

Тест фазы 5: backend/tests/integration/test_plan_template_system.py

Документация фазы: Создать docs/guides/PLAN_TEMPLATES.md (полный обзор)

Коммит фазы: feat(phase5): система шаблонов планов

---

ФАЗА 6: A/B тестирование планов
Цель: Генерация и сравнение альтернативных планов.

Этап 6.1: Генерация альтернативных планов
Шаг 6.1.1: Реализовать генерацию нескольких вариантов плана
Файлы:

backend/app/services/planning_service.py
Новый метод generate_alternative_plans()
Задача:

Генерация 2-3 альтернативных вариантов плана
Параллельное выполнение для скорости
Различные стратегии для каждого варианта
Тесты:

Частный: backend/tests/test_alternative_plan_generation.py
Общий: Интеграция с PlanningService
Документация: Создать docs/guides/PLAN_AB_TESTING.md

Коммит: feat(phase6.1.1): генерация альтернативных планов

Шаг 6.1.2: Реализовать систему оценки планов
Файлы:

backend/app/services/plan_evaluation_service.py (новый)
Задача:

Оценка планов по критериям:
Ожидаемое время выполнения
Количество точек утверждения
Уровень риска
Эффективность (минимальное количество шагов)
Ранжирование планов
Тесты:

Частный: backend/tests/test_plan_evaluation.py
Общий: Интеграция
Документация: Обновить документацию

Коммит: feat(phase6.1.2): система оценки планов

Шаг 6.1.3: Интегрировать в PlanningService
Файлы:

backend/app/services/planning_service.py
Опциональный режим генерации альтернатив
Задача:

Добавить параметр generate_alternatives в generate_plan()
Если включен - генерировать альтернативы и выбирать лучший
Сохранять все варианты для сравнения
Тесты:

Частный: Тесты интеграции
Общий: Полный цикл A/B тестирования
Документация: Обновить документацию

Коммит: feat(phase6.1.3): интеграция A/B тестирования в PlanningService

Тест этапа 6.1: backend/tests/integration/test_alternative_plans.py

Документация этапа: Обновить docs/guides/PLAN_AB_TESTING.md

Коммит этапа: feat(phase6.1): генерация альтернативных планов

---

Этап 6.2: UI для сравнения планов
Шаг 6.2.1: Создать страницу сравнения альтернативных планов
Файлы:

frontend/templates/plans/compare.html (новый)
Задача:

Отображение нескольких вариантов плана рядом
Выделение различий
Оценки и рекомендации
Тесты:

Частный: Мануальное тестирование
Общий: E2E тест сравнения
Документация: Обновить docs/WEB_INTERFACE.md

Коммит: feat(phase6.2.1): страница сравнения планов

Тест этапа 6.2: E2E тест UI сравнения

Документация этапа: Обновить документацию

Коммит этапа: feat(phase6.2): UI для сравнения планов

---

Тест фазы 6: backend/tests/integration/test_plan_ab_testing.py

Документация фазы: Создать docs/guides/PLAN_AB_TESTING.md (полный обзор)

Коммит фазы: feat(phase6): A/B тестирование планов

---

ФАЗА 7: Команды агентов
Цель: Реализовать систему команд специализированных агентов.

Этап 7.1: Модель команды агентов
Шаг 7.1.1: Создать модель AgentTeam
Файлы:

backend/app/models/agent_team.py (новый)
Миграция 024_add_agent_teams.py
Задача:

Модель команды агентов
Поля: name, description, roles, coordination_strategy
Связь с агентами через промежуточную таблицу
Тесты:

Частный: backend/tests/test_agent_team_model.py
Общий: Интеграция с БД
Документация: Создать docs/guides/AGENT_TEAMS.md

Коммит: feat(phase7.1.1): модель AgentTeam

Шаг 7.1.2: Реализовать AgentTeamService
Файлы:

backend/app/services/agent_team_service.py (новый)
Задача:

Создание команды
Назначение ролей агентам
Управление составом команды
Тесты:

Частный: backend/tests/test_agent_team_service.py
Общий: Интеграция
Документация: Обновить документацию

Коммит: feat(phase7.1.2): AgentTeamService

Тест этапа 7.1: backend/tests/integration/test_agent_teams.py

Документация этапа: Обновить docs/guides/AGENT_TEAMS.md

Коммит этапа: feat(phase7.1): модель команды агентов

---

Этап 7.2: Координация работы команды
Шаг 7.2.1: Реализовать координацию через A2A протокол
Файлы:

backend/app/services/agent_team_service.py
Использование существующего A2A Router
Задача:

Распределение задач между агентами команды
Координация выполнения
Передача результатов между агентами
Тесты:

Частный: Тесты координации
Общий: Полный цикл работы команды
Документация: Обновить документацию

Коммит: feat(phase7.2.1): координация команды через A2A

Шаг 7.2.2: Интегрировать команды в PlanningService
Файлы:

backend/app/services/planning_service.py
Использование команд при назначении агентов шагам
Задача:

Выбор команды агентов для задачи
Распределение шагов плана между агентами команды
Координация выполнения
Тесты:

Частный: Тесты интеграции
Общий: Полный цикл планирования с командой
Документация: Обновить документацию

Коммит: feat(phase7.2.2): интеграция команд в PlanningService

Тест этапа 7.2: backend/tests/integration/test_agent_team_coordination.py

Документация этапа: Обновить документацию

Коммит этапа: feat(phase7.2): координация работы команды

---

Тест фазы 7: backend/tests/integration/test_agent_teams_complete.py

Документация фазы: Создать docs/guides/AGENT_TEAMS.md (полный обзор)

Коммит фазы: feat(phase7): команды агентов

---

ФАЗА 8: Диалог между агентами
Цель: Реализовать полноценные диалоги между агентами для совместного решения задач.

Этап 8.1: Система диалога агентов
Шаг 8.1.1: Создать модель AgentConversation
Файлы:

backend/app/models/agent_conversation.py (новый)
Миграция 025_add_agent_conversations.py
Задача:

Модель для хранения диалогов между агентами
Поля: participants, messages, context, goal
Связь с задачами
Тесты:

Частный: backend/tests/test_agent_conversation_model.py
Общий: Интеграция
Документация: Создать docs/guides/AGENT_DIALOGS.md

Коммит: feat(phase8.1.1): модель AgentConversation

Шаг 8.1.2: Реализовать AgentDialogService
Файлы:

backend/app/services/agent_dialog_service.py (новый)
Задача:

Создание диалога между агентами
Добавление сообщений в диалог
Управление контекстом диалога
Определение завершения диалога
Тесты:

Частный: backend/tests/test_agent_dialog_service.py
Общий: Полный цикл диалога
Документация: Обновить документацию

Коммит: feat(phase8.1.2): AgentDialogService

Тест этапа 8.1: backend/tests/integration/test_agent_dialogs.py

Документация этапа: Обновить docs/guides/AGENT_DIALOGS.md

Коммит этапа: feat(phase8.1): система диалога агентов

---

Этап 8.2: Интеграция диалогов в workflow
Шаг 8.2.1: Интегрировать диалоги в PlanningService
Файлы:

backend/app/services/planning_service.py
Использование диалогов для сложных задач
Задача:

Для сложных задач инициировать диалог между агентами
Использовать результаты диалога для создания плана
Сохранять контекст диалога в Digital Twin
Тесты:

Частный: Тесты интеграции
Общий: Полный цикл планирования с диалогом
Документация: Обновить документацию

Коммит: feat(phase8.2.1): интеграция диалогов в PlanningService

Шаг 8.2.2: Создать API для управления диалогами
Файлы:

backend/app/api/routes/agent_dialogs.py (новый)
Задача:

POST /api/agent-dialogs/ - создание диалога
POST /api/agent-dialogs/{dialog_id}/message - добавление сообщения
GET /api/agent-dialogs/{dialog_id} - получение диалога
Тесты:

Частный: backend/tests/test_agent_dialog_api.py
Общий: Интеграция
Документация: Обновить API документацию

Коммит: feat(phase8.2.2): API для управления диалогами

Тест этапа 8.2: backend/tests/integration/test_agent_dialog_workflow.py

Документация этапа: Обновить документацию

Коммит этапа: feat(phase8.2): интеграция диалогов в workflow

---

Тест фазы 8: backend/tests/integration/test_agent_dialogs_complete.py

Документация фазы: Создать docs/guides/AGENT_DIALOGS.md (полный обзор)

Коммит фазы: feat(phase8): диалог между агентами

---

ФАЗА 9: Очистка и реорганизация проекта
Цель: Навести порядок в проекте, удалить лишнее, улучшить структуру.

Этап 9.1: Анализ и очистка кода
Шаг 9.1.1: Провести аудит кода на дублирование
Файлы:

Все файлы проекта
Задача:

Найти дублированный код
Выявить неиспользуемые функции
Определить устаревшие компоненты
Тесты:

Частный: Проверка покрытия тестами
Общий: Запуск всех тестов после очистки
Документация: Создать docs/TECHNICAL_DEBT.md

Коммит: refactor(phase9.1.1): аудит кода на дублирование

Шаг 9.1.2: Удалить или переместить неиспользуемый код
Файлы:

Определить в процессе аудита
Задача:

Удалить неиспользуемые файлы
Переместить код в правильные места
Обновить импорты
Тесты:

Частный: Проверка что ничего не сломалось
Общий: Полный прогон тестов
Документация: Обновить документацию

Коммит: refactor(phase9.1.2): удаление неиспользуемого кода

Шаг 9.1.3: Консолидировать дублированный функционал
Файлы:

Файлы с дублированием
Задача:

Выделить общий функционал в отдельные модули
Использовать общие утилиты
Улучшить переиспользование кода
Тесты:

Частный: Тесты общих модулей
Общий: Проверка что все работает
Документация: Обновить документацию

Коммит: refactor(phase9.1.3): консолидация дублированного функционала

Тест этапа 9.1: Полный прогон всех тестов

Документация этапа: Обновить docs/TECHNICAL_DEBT.md

Коммит этапа: refactor(phase9.1): анализ и очистка кода

---

Этап 9.2: Улучшение структуры документации
Шаг 9.2.1: Реорганизовать документацию
Файлы:

Вся папка docs/
Задача:

Упорядочить структуру документации
Объединить связанные документы
Удалить устаревшие документы
Создать индекс документации
Тесты:

Частный: Проверка ссылок в документации
Общий: Проверка доступности документации
Документация: Создать docs/README.md с навигацией

Коммит: docs(phase9.2.1): реорганизация документации

Шаг 9.2.2: Обновить главный README
Файлы:

README.md
Задача:

Обновить описание проекта
Добавить ссылки на новую документацию
Обновить статус реализации
Добавить примеры использования новых компонентов
Тесты:

Частный: Проверка корректности ссылок
Общий: Проверка читаемости
Документация: Обновить README

Коммит: docs(phase9.2.2): обновление главного README

Тест этапа 9.2: Проверка структуры документации

Документация этапа: Создать docs/README.md

Коммит этапа: docs(phase9.2): улучшение структуры документации

---

Тест фазы 9: Полный прогон всех тестов + проверка документации

Документация фазы: Создать docs/PROJECT_CLEANUP.md

Коммит фазы: refactor(phase9): очистка и реорганизация проекта

---

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