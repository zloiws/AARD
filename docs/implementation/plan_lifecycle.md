# PlanLifecycle (AARD)

## Purpose

`PlanLifecycle` defines an explicit state machine for `Plan.status` so that plan execution is **controllable**, **traceable**, and **non-implicit**.

In AARD terms:
- a plan is a **hypothesis**
- execution is only allowed after **APPROVED**
- failures do not overwrite history; they transition the plan to a terminal state

## Canonical states

Stored as lowercase strings in DB (see `backend/app/models/plan.py`).

- `draft`
- `approved`
- `executing`
- `completed`
- `failed`
- `cancelled`

## Allowed transitions

Defined in `backend/app/planning/lifecycle.py`:

- `draft` → `approved`, `cancelled`
- `approved` → `executing`, `cancelled`
- `executing` → `completed`, `failed`, `cancelled`
- `completed` → (none)
- `failed` → (none)
- `cancelled` → (none)

## Enforcement points (current)

- **Approve:** `backend/app/services/planning_service.py` validates `draft -> approved`.
- **Execute:** `backend/app/api/routes/plans.py` validates `approved -> executing` before calling `ExecutionService`.
- **Orchestrator auto-approval:** when auto-approving, `approved_at` is set to keep metadata consistent (`backend/app/core/request_orchestrator.py`).

## Tests

- `backend/tests/planning/test_plan_lifecycle.py` asserts:
  - `draft -> executing` is rejected
  - `/api/plans/{id}/execute` rejects draft plans


