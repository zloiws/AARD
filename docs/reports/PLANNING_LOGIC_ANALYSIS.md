# Анализ логики построения запросов к моделям и планирования

## Текущее состояние

### 1. Логика построения запросов

#### Анализ задачи (`_analyze_task`)
- **System Prompt**: Четко определяет роль модели как эксперта по анализу задач и стратегическому планированию
- **User Prompt**: Формируется из описания задачи + контекст (JSON)
- **Модель**: Использует `ModelSelector.get_planning_model()` для выбора модели планирования
- **Timeout**: 5 минут для предотвращения зависаний

#### Декомпозиция задачи (`_decompose_task`)
- **System Prompt**: Детальное описание структуры шагов (step_id, description, type, inputs, outputs, timeout, retry_policy, dependencies, approval_required, risk_level, function_call)
- **User Prompt**: Задача + Стратегия + Контекст
- **Модель**: Использует ту же модель планирования
- **Timeout**: 5 минут

### 2. Потенциальные проблемы

#### Проблема 1: Отсутствие контекста задачи в промптах
**Текущее состояние:**
- Промпты формируются только из описания задачи и опционального контекста
- Нет доступа к Digital Twin контексту (история, предыдущие планы, артефакты)

**Решение:**
- Интегрировать Digital Twin контекст в промпты
- Добавить историю предыдущих попыток планирования
- Включить информацию о существующих артефактах

#### Проблема 2: Нет проверки формата ответа
**Текущее состояние:**
- Парсинг JSON происходит после получения ответа
- При ошибке парсинга используется fallback стратегия

**Решение:**
- Добавить валидацию структуры JSON перед сохранением
- Улучшить парсинг JSON (поиск JSON в тексте)
- Добавить попытки исправления некорректного JSON

#### Проблема 3: Контекст не используется эффективно
**Текущее состояние:**
- Контекст передается как JSON строка в промпт
- Нет структурированного использования контекста из Digital Twin

**Решение:**
- Использовать структурированный контекст из Digital Twin
- Включать в промпт только релевантные части контекста
- Добавить примеры из предыдущих успешных планов

### 3. Рекомендации по улучшению

#### Улучшение 1: Интеграция Digital Twin контекста

```python
async def _analyze_task_with_context(
    self,
    task_description: str,
    task_id: Optional[UUID] = None,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Analyze task with full Digital Twin context"""
    
    # Get Digital Twin context if task exists
    digital_twin_context = {}
    if task_id:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            digital_twin_context = task.get_context()
    
    # Build enhanced context
    enhanced_context = {
        "original_request": digital_twin_context.get("original_user_request"),
        "previous_plans": digital_twin_context.get("historical_todos", []),
        "existing_artifacts": digital_twin_context.get("artifacts", []),
        "interaction_history": digital_twin_context.get("interaction_history", [])[-5:],  # Last 5 interactions
        **(context or {})
    }
    
    # Use enhanced context in prompt
    context_str = json.dumps(enhanced_context, indent=2, ensure_ascii=False)
    user_prompt = f"""Task: {task_description}

Previous Context:
{context_str}

Analyze this task considering the previous context and create a strategic plan. Return only valid JSON."""
```

#### Улучшение 2: Улучшенная валидация JSON

```python
def _parse_and_validate_json(self, response_text: str, expected_keys: List[str] = None) -> Dict[str, Any]:
    """Parse JSON with validation and error recovery"""
    # Try multiple JSON extraction methods
    json_data = None
    
    # Method 1: Try to find JSON object/array in response
    json_match = re.search(r'\{.*\}|\[.*\]', response_text, re.DOTALL)
    if json_match:
        try:
            json_data = json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Method 2: Try to parse entire response
    if not json_data:
        try:
            json_data = json.loads(response_text)
        except json.JSONDecodeError:
            pass
    
    # Method 3: Try to fix common JSON errors
    if not json_data:
        try:
            # Fix trailing commas
            fixed_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
            json_data = json.loads(fixed_text)
        except json.JSONDecodeError:
            pass
    
    # Validate structure if expected_keys provided
    if json_data and expected_keys:
        for key in expected_keys:
            if key not in json_data:
                json_data[key] = None  # Set default value
    
    return json_data or {}
```

#### Улучшение 3: Структурированное использование контекста

```python
def _build_enhanced_prompt(
    self,
    task_description: str,
    task_id: Optional[UUID] = None,
    context: Optional[Dict[str, Any]] = None
) -> str:
    """Build enhanced prompt with Digital Twin context"""
    
    # Get Digital Twin context
    digital_twin_context = {}
    if task_id:
        task = self.db.query(Task).filter(Task.id == task_id).first()
        if task:
            digital_twin_context = task.get_context()
    
    # Build structured context sections
    sections = []
    
    # Original request
    if digital_twin_context.get("original_user_request"):
        sections.append(f"Original Request:\n{digital_twin_context['original_user_request']}")
    
    # Previous plans (if any)
    if digital_twin_context.get("historical_todos"):
        sections.append(f"\nPrevious Plans:\n{json.dumps(digital_twin_context['historical_todos'], indent=2)}")
    
    # Existing artifacts
    if digital_twin_context.get("artifacts"):
        sections.append(f"\nExisting Artifacts:\n{json.dumps(digital_twin_context['artifacts'], indent=2)}")
    
    # Recent interactions
    interaction_history = digital_twin_context.get("interaction_history", [])
    if interaction_history:
        recent = interaction_history[-3:]  # Last 3 interactions
        sections.append(f"\nRecent Interactions:\n{json.dumps(recent, indent=2)}")
    
    # Additional context
    if context:
        sections.append(f"\nAdditional Context:\n{json.dumps(context, indent=2)}")
    
    # Build final prompt
    context_str = "\n".join(sections) if sections else ""
    
    return f"""Task: {task_description}

{context_str if context_str else ''}

Please analyze this task and create a strategic plan. Return only valid JSON."""
```

### 4. Выводы

**Текущая логика:**
- ✅ Корректная структура промптов
- ✅ Правильное использование ModelSelector
- ✅ Есть timeout для предотвращения зависаний
- ✅ Есть fallback стратегии

**Что можно улучшить:**
- ❌ Интеграция Digital Twin контекста
- ❌ Улучшенная валидация и парсинг JSON
- ❌ Структурированное использование контекста
- ❌ Добавление примеров из предыдущих успешных планов

**Следующие шаги:**
1. Интегрировать Digital Twin контекст в промпты планирования
2. Улучшить валидацию и парсинг JSON ответов
3. Добавить структурированное использование контекста
4. Протестировать с моделью gemma3:4b на Server 2 - Coding

