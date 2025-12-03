# Интеграция планирования с утверждениями

## Реализовано

### 1. База данных
- ✅ Миграция `004_add_plan_id_to_approval_requests.py`
- ✅ Добавлено поле `plan_id` в таблицу `approval_requests`
- ✅ Добавлен внешний ключ и индекс

### 2. Модель данных
- ✅ Обновлена модель `ApprovalRequest` с полем `plan_id`
- ✅ Добавлена связь с моделью `Plan`

### 3. Автоматическое создание approval request
- ✅ При создании плана автоматически создается approval request
- ✅ Оценка рисков включается в approval request
- ✅ Рекомендации формируются на основе уровня риска

### 4. Обработка утверждения
- ✅ При утверждении approval request план автоматически переходит в статус `approved`
- ✅ Обновлен метод `_approve_plan` для работы с `plan_id`

### 5. UI интеграция
- ✅ На странице плана показывается связанный approval request
- ✅ На странице утверждения показывается связанный план
- ✅ Улучшено отображение планов в списке утверждений
- ✅ Добавлены ссылки между планами и утверждениями

### 6. Исправления
- ✅ Исправлена обработка рисков (числовые значения вместо строк)
- ✅ Улучшена обработка типов данных

## Тестирование
- ✅ Все тесты пройдены успешно
- ✅ Миграция применена
- ✅ Интеграция работает корректно

## Измененные файлы

**Backend:**
- `backend/alembic/versions/004_add_plan_id_to_approval_requests.py` - миграция
- `backend/app/models/approval.py` - добавлено поле plan_id
- `backend/app/services/approval_service.py` - обработка plan_id
- `backend/app/services/planning_service.py` - автоматическое создание approval request
- `backend/app/api/routes/plans_pages.py` - загрузка approval request
- `backend/app/api/routes/approvals_pages.py` - загрузка связанного плана
- `backend/test_plan_approval_integration.py` - тесты

**Frontend:**
- `frontend/templates/plans/detail.html` - информация о approval request
- `frontend/templates/approvals/detail.html` - информация о связанном плане
- `frontend/templates/approvals/queue.html` - улучшенное отображение планов
- `frontend/templates/plans/list.html` - кнопка "Утвердить"

**Документация:**
- `PLAN_APPROVAL_INTEGRATION.md`
- `PLAN_APPROVAL_UI_INTEGRATION.md`
- `TEST_PLAN_APPROVAL_RESULTS.md`

