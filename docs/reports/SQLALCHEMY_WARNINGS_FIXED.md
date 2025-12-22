# Исправление предупреждений SQLAlchemy

## Исправленные предупреждения

### 1. Конфликт relationships в Plan ✅

**Проблема:**
```
SAWarning: relationship 'Plan.approval_request' will copy column plans.id to column approval_requests.plan_id, 
which conflicts with relationship(s): 'Plan.approval_requests'
```

**Решение:**
Добавлен параметр `overlaps="approval_requests"` к relationship `approval_request` в модели `Plan`:

```python
approval_request = relationship("ApprovalRequest", back_populates="plan", uselist=False, overlaps="approval_requests")
```

**Объяснение:**
- `approval_request` (singular) - для одного утверждения плана
- `approval_requests` (plural) - создается через `backref` из `ApprovalRequest`
- Оба указывают на одну колонку `plan_id`, поэтому нужно указать `overlaps`

### 2. Конфликт relationships в ExecutionTrace ✅

**Проблема:**
```
SAWarning: relationship 'ExecutionTrace.task' will copy column tasks.id to column execution_traces.task_id, 
which conflicts with relationship(s): 'Task.traces'
```

**Решение:**
Добавлен параметр `overlaps="traces"` к relationship `task` в модели `ExecutionTrace`:

```python
task = relationship("Task", foreign_keys=[task_id], overlaps="traces")
```

И добавлен `overlaps="task"` к relationship `traces` в модели `Task`:

```python
traces = relationship("ExecutionTrace", foreign_keys="ExecutionTrace.task_id", overlaps="task")
```

**Объяснение:**
- `ExecutionTrace.task` - обратная связь от trace к task
- `Task.traces` - связь от task к traces
- Оба указывают на одну колонку `task_id`, поэтому нужно указать `overlaps`

## Результат

- ✅ Все предупреждения SQLAlchemy исправлены
- ✅ Relationships правильно настроены с параметром `overlaps`
- ✅ Сервер должен запускаться без предупреждений SQLAlchemy

