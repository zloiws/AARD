# 🔍 Анализ причины проблемы с моделью "huihui_ai/deepseek-r1-abliterated:8b"

## Проблема

Модель `huihui_ai/deepseek-r1-abliterated:8b` всегда используется, даже когда выбрана другая модель или сервер.

## Причина

### Цепочка вызовов:

1. **Frontend (`handleSubmit`):**
   - Если пользователь не выбирает сервер/модель, `serverId` и `model` остаются пустыми строками `""`
   - Пустые строки НЕ передаются в API (проверка `if (serverId && serverId.trim())`)

2. **Backend (`chat.py`):**
   - Если `server_id` не передан → `selected_server_url = None`
   - Если `model` не передан → `selected_model = None`
   - Вызывается `client.generate()` с `server_url=None` и `model=None`

3. **OllamaClient (`ollama_client.py`):**
   - Срабатывает **PRIORITY 3** (автоматический выбор):
   ```python
   # PRIORITY 3: Auto-select based on task type
   else:
       instance = self.select_model_for_task(task_type)
       if not instance:
           # Fallback to first available instance
           for inst in self.instances:  # <-- ЭТО ИЗ .env!
               if await self.health_check(inst):
                   instance = inst
                   break
       actual_model_name = None  # <-- НЕ УСТАНОВЛЕН!
   ```
   - `self.instances` загружается из `.env` (строки 78-81):
   ```python
   self._instances = [
       self.settings.ollama_instance_1,  # <-- ИЗ .env!
       self.settings.ollama_instance_2,  # <-- ИЗ .env!
   ]
   ```

4. **Финальный выбор модели:**
   ```python
   model_to_use = actual_model_name if actual_model_name else instance.model
   ```
   - `actual_model_name = None` → используется `instance.model` из `.env`
   - Это и есть `"huihui_ai/deepseek-r1-abliterated:8b"`!

## Дополнительные проблемы

### PRIORITY 2 (когда `model` передан, но `server_url` нет):
```python
elif model:
    # Try to find instance by exact model name match
    for inst in self.instances:  # <-- ИЩЕТ В .env, А НЕ В БД!
```
- Ищет модель в `.env` конфигурации, а не в БД
- Если не находит, использует первый доступный инстанс из `.env`

### PRIORITY 1 (когда `server_url` передан, но `model` нет):
```python
if server_url:
    if model:
        # OK - создает динамический инстанс
    else:
        # Пробует найти в .env конфигурации
        instance = self._find_instance_by_url(server_url)  # <-- ИЩЕТ В .env!
```
- Ищет сервер в `.env`, а не в БД

## Решение

Нужно полностью убрать зависимость от `.env` конфигурации и использовать только БД:

1. **Когда `server_id` передан:**
   - Получить сервер из БД
   - Если `model` не передан, получить модели из БД и выбрать подходящую

2. **Когда ни `server_id`, ни `model` не переданы:**
   - Использовать БД для автоматического выбора
   - Получить сервер по умолчанию из БД
   - Выбрать модель на основе `task_type` из БД

3. **Убрать fallback на `.env`:**
   - Не использовать `self.instances` из `.env`
   - Всегда использовать БД через `OllamaService`

