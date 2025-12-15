# AARD — Comprehensive Development Plan v0.2

**Status:** canonical, loadable into Cursor AI as project plan

---

## 0. Foundational Premises (Non‑Negotiable)

These premises are architectural constraints. Any implementation, refactor, or extension **must not violate them**.

1. **AARD is not a product, agent, or service**  
   AARD is a **personal human–AI interaction environment**.

2. **Human is the foundation of the system, not a supervisor**  
   Human provides intent, criteria, examples, and corrections — but is not an oracle of truth.

3. **LLM is a semantic interpreter**  
   LLM converts language → structured intent → candidate actions. It is not an intelligence core.

4. **Plans are hypotheses**  
   Every plan represents an assumption about how to satisfy intent and may be wrong.

5. **Examples are initialization, not learning**  
   Examples reduce ambiguity but do not directly change behavior.

6. **Learning occurs only through reflection on outcomes**  
   Successful and unsuccessful executions are analyzed to derive interpretation rules.

7. **No direct behavior change without reflection**  
   Neither human feedback nor examples may directly alter planning or execution logic.

---

## 1. Conceptual Learning Loop (Canonical)

```
Intent
  ↓
Interpretation (using current rules)
  ↓
Plan (hypothesis)
  ↓
Execution
  ↓
Outcome
  ↓
Reflection
  ↓
Derived interpretation rules
  ↓
Future interpretation bias
```

There is **no shortcut** in this loop.

---

## 2. Core Architectural Domains

### 2.1 Human Domain

#### Human
- Source of intent
- Source of criteria
- Source of examples
- Source of corrections

#### UserContext (HumanState)
Stores:
- preferences
- risk tolerance
- trust level
- historical corrections
- fatigue / urgency signals (if available)

UserContext **influences interpretation**, never execution directly.

---

### 2.2 Intent & Meaning Domain

#### IntentAlignmentService
**Purpose:** align raw input with intended meaning.

Responsibilities:
- detect ambiguity
- request clarification
- require examples when explanation is insufficient
- output structured `Intent`

Constraints:
- must refuse to guess silently
- must surface uncertainty explicitly

Artifacts:
- Intent
- ClarificationRequest

---

### 2.3 Interpretation Domain

#### InterpretationRule
A derived, fallible bias used during interpretation.

Fields:
- condition
- preferred interpretation strategy
- confidence score
- source (reflection / repeated success / repeated failure)
- temporal weight

Rules **decay over time** if not reinforced.

#### InterpretationRuleset
- collection of active InterpretationRules
- queried by RequestRouter and PlanningService

---

### 2.4 Planning Domain

#### PlanningService
**Purpose:** generate candidate plans as hypotheses.

Inputs:
- Intent
- UserContext
- InterpretationRuleset
- MemoryService

Outputs:
- PlanObject (state = DRAFT)

PlanningService **must not assume correctness**.

---

#### PlanLifecycle
Explicit state machine for plans.

States:
- DRAFT
- HYPOTHESIS
- APPROVED
- EXECUTING
- EXECUTED
- FAILED
- DEPRECATED

Rules:
- no execution without APPROVED
- failures do not overwrite past plans
- deprecated plans remain analyzable

---

### 2.5 Execution Domain

#### ExecutionService
**Purpose:** attempt execution of an approved plan.

Responsibilities:
- enforce CapabilityBoundary
- track execution steps
- emit structured outcomes

Outputs:
- ExecutionResult
- ExecutionTrace

ExecutionService **never modifies interpretation rules**.

---

#### CapabilityBoundary
Defines what actions are allowed.

Sources:
- system policy
- user constraints
- environment constraints

Violations produce explicit failures, not retries.

---

### 2.6 Reflection Domain (Core Learning Layer)

#### ReflectionService
**Purpose:** analyze outcomes against intent and plan.

Inputs:
- PlanObject
- ExecutionResult
- ExecutionTrace
- Human feedback (as data)

Outputs:
- ReflectionRecord

Reflection categories:
- success
- partial success
- semantic mismatch
- execution failure
- goal drift

---

#### MetaLearningService (Strictly Non‑Magical)

**Purpose:** derive InterpretationRules from reflection records.

Rules:
- does not modify models
- does not modify code
- does not modify agents

Outputs:
- new InterpretationRules
- confidence adjustments
- rule deprecations

---

### 2.7 Feedback Domain

#### FeedbackLearningService
**Purpose:** ingest human feedback as raw data.

Rules:
- feedback does not imply correctness
- feedback enters only ReflectionService

---

### 2.8 Memory & Time Domain

#### MemoryService
Stores:
- examples
- past intents
- plans
- reflections

Memory is **queryable but non‑authoritative**.

---

#### DecisionHistory (Timeline)

Records:
- intent → interpretation → plan → execution → outcome → reflection

Used for:
- debugging
- visualization
- trust building
- future commercial value

---

## 3. Visualization & Real‑Time Introspection (Mandatory)

AARD must be able to render, in real time:

- active intent
- current interpretation rules applied
- plan graph
- execution steps
- decision points
- reflection outcomes

### Visualization Requirements

- node‑based graph
- temporal ordering
- explicit "why" edges
- replayable sessions

Every arrow **must be explainable**.

---

## 4. Agent Model (Strictly Bounded)

Agents are **tools**, not actors.

### PlannerAgent
- assists PlanningService
- proposes plan variants

### CoderAgent
- assists ExecutionService
- produces executable artifacts

### AgentTeamCoordination
- orchestration only
- no independent goals

Agents **do not learn**.

---

## 5. Development Phases (Cursor Execution Order)

### Phase 1 — Ontology First
- define all core data models
- no behavior, no logic

### Phase 2 — PlanLifecycle
- implement state machine
- exhaustive unit tests

### Phase 3 — IntentAlignment
- ambiguity handling
- example‑request logic

### Phase 4 — Reflection Loop
- ReflectionService
- MetaLearningService
- InterpretationRules

### Phase 5 — Execution & Boundaries
- CapabilityBoundary
- ExecutionService

### Phase 6 — Visualization Layer
- graph schema
- event emission
- replay

### Phase 7 — Integration & Regression
- end‑to‑end flows
- failure‑first testing

---

## 6. Non‑Goals (Explicitly Out of Scope)

- AGI
- autonomous self‑improvement
- model training
- universal assistant
- optimization without explanation

---

## 7. Final Canonical Definition

**AARD is a personal human–AI interaction environment in which system actions are treated as hypotheses, and behavioral evolution emerges exclusively through reflection on the outcomes of those actions in the context of human intent.**

---

**This document is authoritative.**

