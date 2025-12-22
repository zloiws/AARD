# Service: Agents & Planning

Role: Agent implementations (Component + Capabilities) and plan lifecycle management.

## Contract

### Inputs
- Task descriptions, prompts, memory/context

### Outputs
- Plans, actions, agent messages

### Errors
- `AGENT_RUNTIME_ERROR` — agent internal failure
- `PROMPT_RESOLUTION_ERROR` — failed to resolve system prompt

### LLM usage
- uses_llm: yes (agents are Components per ARCHITECTURE_LAW.md)
- prompt_id: VERIFY (must be registered in PromptAssignment)

### Owner
- TODO

### Notes
- Agents must be registered in Registry and have explicit system prompts.


