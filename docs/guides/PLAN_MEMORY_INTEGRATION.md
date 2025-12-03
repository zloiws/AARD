# Plan-Memory Integration

## Overview

The AARD platform integrates plan lifecycle with the memory system, providing three types of memory integration:

1. **Working Memory**: Active ToDo list for current tasks
2. **Episodic Memory**: History of all plan changes
3. **Procedural Memory**: Templates of successful plans for reuse

## Working Memory

Working memory stores the active ToDo list for a task, allowing agents to track what needs to be done.

### Implementation

- **Storage**: Uses `MemoryEntry` (short-term memory) with `context_key="task_{task_id}_todo"`
- **Content**: List of plan steps with status (pending/completed)
- **TTL**: 7 days (configurable)
- **Session**: Linked to task_id

### Usage

```python
# Automatically saved when plan is created/updated
await planning_service._save_todo_to_working_memory(task_id, plan)

# Retrieve ToDo list
memory_service = MemoryService(db)
todo_context = memory_service.get_context(
    agent_id=agent_id,
    context_key=f"task_{task_id}_todo",
    session_id=str(task_id)
)
```

### Content Structure

```json
{
    "task_id": "uuid",
    "plan_id": "uuid",
    "plan_version": 1,
    "todo_list": [
        {
            "step_id": "step_1",
            "description": "Step description",
            "status": "pending",
            "completed": false
        }
    ],
    "total_steps": 5,
    "completed_steps": 0,
    "updated_at": "2025-12-03T20:00:00"
}
```

## Episodic Memory

Episodic memory stores the complete history of plan changes, allowing the system to learn from past planning decisions.

### Implementation

- **Storage**: Uses `AgentMemory` with `memory_type="experience"`
- **Content**: Full plan snapshot with context
- **Tags**: `["plan", "episodic", event_type, "task_{task_id}"]`
- **Importance**: 0.7 (high importance)

### Events Tracked

1. **plan_created**: When a new plan is created
2. **plan_replanned**: When a plan is replanned after failure
3. **plan_updated**: When a plan is modified (future)
4. **plan_approved**: When a plan is approved (future)
5. **plan_executed**: When a plan execution completes (future)

### Usage

```python
# Automatically saved when plan events occur
await planning_service._save_plan_to_episodic_memory(
    plan=plan,
    task_id=task_id,
    event_type="plan_created",
    context={"additional": "context"}
)

# Retrieve plan history
memories = memory_service.get_memories(
    agent_id=agent_id,
    memory_type="experience",
    tags=["plan", "episodic"]
)
```

### Content Structure

```json
{
    "plan_id": "uuid",
    "plan_version": 1,
    "task_id": "uuid",
    "task_description": "Task description",
    "event_type": "plan_created",
    "plan_goal": "Plan goal",
    "plan_steps": [...],
    "plan_status": "draft",
    "strategy": {...},
    "timestamp": "2025-12-03T20:00:00",
    "additional_context": "..."
}
```

### Pattern Extraction

The system can extract patterns from episodic memory:

```python
# Example: "In past similar tasks, when we got 403 error, adding User-Agent header helped"
# This pattern is extracted and stored in procedural memory
```

## Procedural Memory

Procedural memory stores templates of successful plans that can be reused for similar tasks.

### Implementation

- **Storage**: Uses `AgentMemory` with `memory_type="pattern"` and `LearningPattern` from MetaLearningService
- **Source**: Extracted from successful plan executions
- **Application**: Automatically applied when generating new plans for similar tasks

### Pattern Sources

1. **Memory Patterns**: Stored in `AgentMemory` with type "pattern"
2. **Learning Patterns**: Stored in `LearningPattern` table via MetaLearningService

### Usage

```python
# Automatically applied during plan generation
procedural_pattern = await planning_service._apply_procedural_memory_patterns(
    task_description="Create user authentication",
    agent_id=agent_id
)

# Pattern is passed to plan generation context
if procedural_pattern:
    # Use pattern to guide plan generation
    steps = await decompose_task_with_pattern(task_description, procedural_pattern)
```

### Pattern Selection

Patterns are ranked by:
1. **Success Rate**: Patterns with > 0.7 success rate
2. **Importance**: Importance score from memory
3. **Relevance**: Similarity to current task

Best matching pattern is automatically applied.

### Pattern Structure

```json
{
    "pattern_type": "strategy",
    "steps_template": [...],
    "success_rate": 0.85,
    "usage_count": 10,
    "last_used": "2025-12-03T20:00:00",
    "applicable_tasks": ["authentication", "user_management"]
}
```

## Integration Points

### Plan Creation

1. **Apply Procedural Memory**: Search for similar successful plans
2. **Generate Plan**: Use patterns if found
3. **Save to Episodic Memory**: Store plan creation event
4. **Save to Working Memory**: Store active ToDo list

### Plan Replanning

1. **Save Failure to Episodic Memory**: Store failure context
2. **Generate New Plan**: With error analysis
3. **Update Episodic Memory**: Store replan event
4. **Update Working Memory**: Update ToDo list

### Plan Execution

1. **Update Working Memory**: Mark steps as completed
2. **Save Success to Episodic Memory**: Store execution result
3. **Extract Patterns**: If successful, extract to procedural memory

## Benefits

1. **Learning**: System learns from past planning decisions
2. **Efficiency**: Reuses successful plan templates
3. **Context Preservation**: Full history of plan changes
4. **Pattern Recognition**: Identifies successful strategies
5. **Error Recovery**: Learns from failures

## Example Workflow

```python
# 1. Generate plan for "Create user authentication"
plan = await planning_service.generate_plan(
    task_description="Create user authentication",
    context={"agent_id": agent_id}
)

# System automatically:
# - Searches procedural memory for similar successful plans
# - Applies pattern if found (e.g., "Use JWT tokens, bcrypt for passwords")
# - Saves plan creation to episodic memory
# - Saves ToDo list to working memory

# 2. Plan execution fails
plan.status = "failed"

# System automatically:
# - Analyzes failure (e.g., "403 Forbidden")
# - Searches episodic memory for similar failures
# - Finds pattern: "In past, adding User-Agent header helped"
# - Replans with fix
# - Saves replan to episodic memory

# 3. New plan succeeds
plan.status = "completed"

# System automatically:
# - Extracts successful pattern
# - Saves to procedural memory
# - Future similar tasks will use this pattern
```

## Related Documentation

- [Memory Service](./MEMORY.md) - Memory system overview
- [Meta-Learning Service](./META_LEARNING.md) - Pattern extraction
- [Task Lifecycle](./TASK_LIFECYCLE.md) - Task status management
- [Automatic Replanning](./AUTOMATIC_REPLANNING.md) - Replanning on failure

