# Исправления интерфейса и интеграция планов

## Исправленные проблемы

### 1. Дублирующая навигация
- ✅ Убрана навигация из шаблонов `approvals/queue.html` и `artifacts/list.html`
- ✅ Удалены неиспользуемые CSS стили для навигации
- ✅ Навигация теперь только на верхнем уровне в `main.html`

### 2. Ошибка UUID при создании плана
- ✅ Исправлен порядок роутов в `plans_pages.py`
- ✅ Роут `/plans/create` теперь перед `/plans/{plan_id}`

### 3. Улучшена цветовая палитра
- ✅ Улучшена читаемость в `approvals/detail.html`
- ✅ Добавлены стили для лучшего контраста в `plans/list.html` и `plans/detail.html`
- ✅ Исправлена вложенность div в `approvals/detail.html`

## Измененные файлы

- `frontend/templates/approvals/queue.html` - убрана дублирующая навигация
- `frontend/templates/artifacts/list.html` - убрана дублирующая навигация
- `frontend/templates/approvals/detail.html` - исправлена вложенность, улучшены цвета
- `frontend/templates/plans/list.html` - улучшена цветовая палитра
- `frontend/templates/plans/detail.html` - улучшена цветовая палитра
- `backend/app/api/routes/plans_pages.py` - исправлен порядок роутов

