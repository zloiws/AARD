# Task Lifecycle Management

## Overview

The AARD platform implements a comprehensive task lifecycle management system that tracks tasks through their entire workflow, from creation to completion or failure. This system provides clear state transitions, role tracking, and graduated autonomy levels.

## Task Status Enum

The `TaskStatus` enum defines all possible states a task can be in:

### Initial States

- **`DRAFT`**: Task created by planner, not yet approved
- **`PENDING`**: Task waiting to start
- **`PLANNING`**: Plan is being generated for the task

### Approval States

- **`PENDING_APPROVAL`**: Task sent for approval (new, preferred)
- **`WAITING_APPROVAL`**: Task waiting for approval (legacy, use `PENDING_APPROVAL`)
- **`APPROVED`**: Task approved by human or validator

### Execution States

- **`IN_PROGRESS`**: Task is executing (new, preferred)
- **`EXECUTING`**: Plan is executing (legacy, use `IN_PROGRESS`)
- **`PAUSED`**: Task temporarily paused
- **`ON_HOLD`**: Task on hold (waiting for data, human, external event)

### Final States

- **`COMPLETED`**: Task successfully completed
- **`FAILED`**: Task failed with error
- **`CANCELLED`**: Task cancelled by human or system

## Task Model Fields

### Workflow Tracking

- **`created_by`**: User who created the task
- **`created_by_role`**: Role of creator (`planner`, `human`, `system`)
- **`approved_by`**: User who approved the task
- **`approved_by_role`**: Role of approver (`human`, `validator`)

### Graduated Autonomy

- **`autonomy_level`**: Integer from 0 to 4, defining the level of autonomy:
  - **Level 0**: Read-only (analysis and suggestions only)
  - **Level 1**: Step-by-step confirmation (approval for each step)
  - **Level 2**: Plan approval (approval required for plan, then autonomous execution)
  - **Level 3**: Autonomous with notification (executes autonomously, sends notifications)
  - **Level 4**: Full autonomous (no human intervention required)

## Workflow Transitions

### Standard Flow

1. **Creation**: Task created with status `DRAFT` and `created_by_role="planner"`
2. **Approval**: If critical steps detected, transition to `PENDING_APPROVAL`
3. **Approval**: Human/validator approves, status becomes `APPROVED`, `approved_by_role` set
4. **Execution**: Status changes to `IN_PROGRESS`
5. **Completion**: Status becomes `COMPLETED` or `FAILED`

### Alternative Flows

- **On Hold**: Task can transition to `ON_HOLD` from `IN_PROGRESS` when waiting for external input
- **Cancellation**: Task can be `CANCELLED` from any state by human or system
- **Replanning**: On `FAILED`, system can automatically replan and create new plan

## Usage Examples

### Creating a Task

```python
from app.models.task import Task, TaskStatus

task = Task(
    description="Implement user authentication",
    status=TaskStatus.DRAFT,
    created_by_role="planner",
    autonomy_level=2
)
```

### Approving a Task

```python
task.status = TaskStatus.APPROVED
task.approved_by = "user@example.com"
task.approved_by_role = "human"
```

### Putting Task on Hold

```python
task.status = TaskStatus.ON_HOLD
# Task will wait for external input before resuming
```

### Cancelling a Task

```python
task.status = TaskStatus.CANCELLED
# Task execution is stopped
```

## Integration with Planning Service

The `PlanningService` automatically creates tasks with:
- Status: `DRAFT`
- `created_by_role`: `"planner"`

Tasks then transition to `PENDING_APPROVAL` if critical steps are detected (see Adaptive Approval Service).

## Integration with Execution Service

The `ExecutionService` transitions tasks:
- From `APPROVED` to `IN_PROGRESS` when execution starts
- To `COMPLETED` on successful completion
- To `FAILED` on error (triggers automatic replanning)

## Database Migration

The task lifecycle extension was added in migration `017_extend_task_lifecycle`:
- Added `created_by_role`, `approved_by`, `approved_by_role` columns
- Added `autonomy_level` column with default value 2
- Extended `TaskStatus` enum with new values

## Best Practices

1. **Always set `created_by_role`** when creating tasks programmatically
2. **Use `PENDING_APPROVAL`** instead of `WAITING_APPROVAL` for new code
3. **Use `IN_PROGRESS`** instead of `EXECUTING` for new code
4. **Set `approved_by_role`** when approving tasks
5. **Respect `autonomy_level`** when making approval decisions

## Related Documentation

- [Adaptive Approval Service](./ADAPTIVE_APPROVAL.md) - Intelligent approval decisions
- [Automatic Replanning](./AUTOMATIC_REPLANNING.md) - Replanning on failure
- [Graduated Autonomy](./GRADUATED_AUTONOMY.md) - Autonomy levels (when implemented)

