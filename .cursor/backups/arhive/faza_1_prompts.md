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
---