# AARD — Interaction & Decision Flow (Reflection-Driven)

Ниже — **обновлённая схема взаимодействий**, строго приведённая в соответствие с утверждённой структурой AARD v0.2.
Схема отражает:
- реальные контуры принятия решений
- точки человеческого участия
- цикл гипотеза → действие → результат → рефлексия
- отсутствие прямого «обучения»

---

## 1. Основной поток взаимодействия

```mermaid
flowchart LR

    %% === HUMAN & INPUT ===
    Human[Human]
    UserRequest[User Request]
    UserContext[UserContext]

    %% === INTENT & ALIGNMENT ===
    IntentAlignment[IntentAlignmentService]
    Intent[Intent]
    Clarification[Clarification / Example Request]

    %% === INTERPRETATION ===
    InterpretationRules[InterpretationRuleset]

    %% === PLANNING ===
    PlanningService[PlanningService]
    PlanLifecycle[PlanLifecycle]
    Plan[Plan (Hypothesis)]

    %% === APPROVAL ===
    Approval[AdaptiveApprovalService]

    %% === EXECUTION ===
    ExecutionService[ExecutionService]
    CapabilityBoundary[CapabilityBoundary]
    Sandbox[Execution Sandbox]
    Outcome[Execution Outcome]

    %% === REFLECTION ===
    ReflectionService[ReflectionService]
    MetaLearning[MetaLearningService]

    %% === MEMORY & HISTORY ===
    Memory[MemoryService]
    DecisionHistory[DecisionHistory]

    %% === FLOW ===
    Human --> UserRequest
    Human --> UserContext

    UserRequest --> IntentAlignment
    IntentAlignment -->|ambiguous| Clarification
    Clarification --> Human
    Clarification --> IntentAlignment

    IntentAlignment --> Intent

    UserContext --> IntentAlignment
    InterpretationRules --> IntentAlignment

    Intent --> PlanningService
    UserContext --> PlanningService
    InterpretationRules --> PlanningService
    Memory --> PlanningService

    PlanningService --> PlanLifecycle
    PlanLifecycle --> Plan

    Plan --> Approval
    Approval -->|approved| ExecutionService
    Approval -->|rejected| PlanningService

    ExecutionService --> CapabilityBoundary
    CapabilityBoundary --> Sandbox
    Sandbox --> Outcome

    ExecutionService --> DecisionHistory
    PlanningService --> DecisionHistory

    Outcome --> ReflectionService
    Human -->|feedback| ReflectionService

    ReflectionService --> MetaLearning
    MetaLearning --> InterpretationRules

    ReflectionService --> Memory
    DecisionHistory --> Memory
```

---

## 2. Ключевые смысловые акценты схемы (что важно не потерять)

### 2.1 План — это гипотеза
- план **не считается правильным по умолчанию**
- утверждение ≠ истина
- выполнение ≠ успех

---

### 2.2 Человек не «правит систему напрямую»
- человеческий фидбек → данные
- вывод → только через ReflectionService
- изменения → только через InterpretationRules

---

### 2.3 Обучение = производное от результата
- нет стрелки `Human → Behavior`
- нет стрелки `Example → Learning`
- есть только `Outcome → Reflection → Rules`

---

## 3. Контур визуализации в реальном времени (как это должно выглядеть в UI)

Каждый запуск запроса должен порождать **временной граф**, где:

- узлы:
  - Intent
  - Applied Interpretation Rules
  - Plan nodes
  - Execution steps
  - Decision points
  - Reflection result

- рёбра:
  - "interpreted as"
  - "planned because"
  - "executed under constraint"
  - "failed due to"
  - "rule derived from"

Любой узел **должен быть кликабельным** с ответом:
> почему это произошло

---

## 4. Минимальный чек-лист корректности архитектуры

Система считается корректной, если:
- [ ] можно восстановить полный путь решения
- [ ] видно, какие правила применялись
- [ ] понятно, где система ошиблась
- [ ] понятно, почему изменилось поведение

Если хотя бы один пункт не выполняется — архитектура нарушена.

---

## 5. Каноническая фиксация

**Это не схема агентов.**  
**Это схема мышления среды.**

Если Cursor предлагает упростить её — он нарушает концепт.

