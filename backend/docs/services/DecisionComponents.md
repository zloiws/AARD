# Service: Decision / Interpretation Components

Role: LLM-based components for interpretation, routing, validation and reflection.

## Contract

### Inputs
- Intermediate outputs, prompts, request context

### Outputs
- Validated decisions, normalized prompts, routing decisions

### Errors
- `VALIDATION_ERROR` — semantic/format validation failed

### LLM usage
- uses_llm: yes (components must have system prompt)
- prompt_id: VERIFY

### Owner
- TODO

### Notes
- Components are required to expose explicit contracts and system prompts per ARCHITECTURE_LAW.md.


