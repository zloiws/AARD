# Automatic Replanning on Failure

## Overview

The AARD platform implements automatic replanning when a plan execution fails. This system analyzes failures, learns from mistakes, and creates improved plans automatically.

## Features

1. **Automatic Failure Detection**: Detects when plan execution fails
2. **Error Analysis**: Uses ReflectionService to analyze failures
3. **Learning from Mistakes**: Saves error patterns to memory for future reference
4. **Automatic Replanning**: Creates new plan version with error context
5. **Approval Integration**: New plans automatically go through approval process

## Workflow

### When a Plan Fails

1. **Failure Detection**: ExecutionService detects failure at any step
2. **Task Status Update**: Task status is updated to `FAILED`
3. **Error Analysis**: ReflectionService analyzes the failure:
   - Error type classification
   - Root cause analysis
   - Contributing factors
   - Similar past situations
4. **Fix Generation**: ReflectionService generates fix suggestions
5. **Learning**: Error pattern is saved to agent memory
6. **Replanning**: New plan is created with:
   - Error analysis context
   - Fix suggestions
   - Similar situations
   - Execution context at failure point
7. **Approval**: New plan goes through approval process
   - If critical steps detected → `PENDING_APPROVAL`
   - Otherwise → adaptive approval logic

## Implementation

### ExecutionService._handle_plan_failure()

This method is automatically called when a plan fails:

```python
async def _handle_plan_failure(
    self,
    plan: Plan,
    error_message: str,
    execution_context: Dict[str, Any]
) -> Optional[Plan]:
    """
    Handle plan failure by analyzing error and automatically replanning
    """
    # 1. Update task status to FAILED
    task.status = TaskStatus.FAILED
    
    # 2. Analyze failure
    reflection_result = await reflection_service.analyze_failure(
        task_description=task.description,
        error=error_message,
        context={...},
        agent_id=agent_id
    )
    
    # 3. Generate fix
    fix_suggestion = await reflection_service.generate_fix(...)
    
    # 4. Save learning pattern
    await reflection_service.learn_from_mistake(...)
    
    # 5. Create new plan
    new_plan = await planning_service.replan(
        plan_id=plan.id,
        reason=f"Plan failed: {error_message}",
        context={
            "error_analysis": reflection_result.analysis,
            "fix_suggestion": fix_suggestion,
            ...
        }
    )
    
    return new_plan
```

### Integration Points

The automatic replanning is triggered in three places in `ExecutionService`:

1. **No steps in plan**: When plan has no steps
2. **Dependency failure**: When required dependency is missing
3. **Step execution failure**: When a step fails during execution

## Error Analysis

### Error Types

The ReflectionService classifies errors into categories:

- **timeout**: Execution timeout
- **permission**: Access denied
- **not_found**: Resource not found
- **invalid_input**: Invalid input data
- **network**: Network/connection issues
- **syntax**: Code syntax errors
- **type_error**: Type mismatch
- **attribute_error**: Missing attribute
- **key_error**: Missing dictionary key
- **value_error**: Invalid value
- **index_error**: Index out of range

### Root Cause Analysis

The system uses LLM to analyze:
- Root cause of failure
- Contributing factors
- Severity assessment
- Preventability

### Similar Situations

The system searches agent memory for similar past failures:
- Same error type
- Similar task descriptions
- Previous fixes that worked

## Learning from Mistakes

When a failure occurs, the system:

1. **Saves Error Pattern**: Stores error type, fix, and root cause
2. **Tags for Search**: Tags with "learning", "pattern", "fix"
3. **High Importance**: Marks as high importance (0.8) for future reference
4. **Agent-Specific**: Saves to specific agent's memory

## Replanning Context

The new plan is created with rich context:

```python
context = {
    "error_analysis": {
        "error_type": "permission",
        "root_cause": "...",
        "contributing_factors": [...]
    },
    "fix_suggestion": {
        "status": "success",
        "message": "...",
        "suggested_changes": [...]
    },
    "similar_situations": [...],
    "execution_context": {...},
    "failed_at_step": 2
}
```

This context is passed to the planner, which can:
- Avoid the same mistake
- Apply suggested fixes
- Learn from similar situations
- Skip already-completed steps

## Plan Versioning

Each replan creates a new version:
- Original plan: version 1
- First replan: version 2
- Second replan: version 3
- etc.

All versions are linked to the same task and can be compared.

## Approval Process

After replanning, the new plan automatically goes through approval:

1. **Critical Step Detection**: Checks for critical operations
2. **Adaptive Approval**: Uses AdaptiveApprovalService to determine if approval needed
3. **Task Status**: 
   - If critical steps → `PENDING_APPROVAL`
   - If auto-approved → `APPROVED`
   - Otherwise → adaptive logic

## Usage Example

```python
# Plan execution fails
plan.status = "failed"

# Automatic replanning is triggered
new_plan = await execution_service._handle_plan_failure(
    plan=plan,
    error_message="Permission denied: cannot write to /protected",
    execution_context={"step_1": {...}, "step_2": {...}}
)

# New plan is created with version 2
assert new_plan.version == 2
assert new_plan.task_id == plan.task_id

# New plan includes error context
assert "error_analysis" in new_plan.context
```

## Benefits

1. **Resilience**: System automatically recovers from failures
2. **Learning**: System learns from mistakes and improves
3. **Efficiency**: No manual intervention needed for common failures
4. **Context Preservation**: Full execution context is preserved
5. **Version History**: All plan versions are tracked

## Limitations

1. **LLM Dependency**: Error analysis depends on LLM availability
2. **Memory Search**: Requires agent memory to be populated
3. **Infinite Loop Risk**: Could replan indefinitely if issue persists
4. **Resource Usage**: Each replan uses LLM tokens

## Future Improvements

- [ ] Maximum replan attempts limit
- [ ] Exponential backoff for repeated failures
- [ ] Human intervention trigger after N failures
- [ ] Better error pattern matching
- [ ] Cross-agent learning

## Related Documentation

- [Reflection Service](./REFLECTION.md) - Error analysis and fix generation
- [Memory Service](./MEMORY.md) - Pattern storage and retrieval
- [Task Lifecycle](./TASK_LIFECYCLE.md) - Task status management
- [Adaptive Approval](./ADAPTIVE_APPROVAL.md) - Approval decisions

