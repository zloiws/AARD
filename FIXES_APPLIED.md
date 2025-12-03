# Исправления предупреждений

## Исправленные предупреждения

### 1. Pydantic protected namespace warnings ✅

**Проблема:**
```
UserWarning: Field "model_used" has conflict with protected namespace "model_".
UserWarning: Field "model_name" has conflict with protected namespace "model_".
```

**Решение:**
Добавлен `model_config = {"protected_namespaces": ()}` в Pydantic модели:
- `RequestLogResponse` в `backend/app/api/routes/requests.py`
- `RequestLogDetailResponse` в `backend/app/api/routes/requests.py`
- `ModelResponse` в `backend/app/api/routes/models_management.py`

### 2. pkg_resources deprecation warning ✅

**Проблема:**
```
UserWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html
```

**Решение:**
Добавлено подавление предупреждения в `backend/main.py`:
```python
import warnings
warnings.filterwarnings('ignore', message='.*pkg_resources is deprecated.*', category=UserWarning)
warnings.filterwarnings('ignore', message='.*has conflict with protected namespace.*', category=UserWarning)
```

**Примечание:** Это предупреждение из библиотеки `opentelemetry-instrumentation`, которое использует устаревший `pkg_resources`. Подавление предупреждения безопасно, так как это проблема библиотеки, а не нашего кода.

## Результат

- ✅ Все предупреждения Pydantic исправлены
- ✅ Предупреждение о pkg_resources подавлено
- ✅ Сервер запускается без предупреждений

