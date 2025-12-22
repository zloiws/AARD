# Service: Registry / Service Discovery

Role: Single source of truth for agents, capabilities, versions and lifecycle.

## Contract

### Inputs
- Service descriptors, registration calls at startup

### Outputs
- Lookup API, registry entries, lifecycle state

### Errors
- `REGISTRY_CONFLICT` — duplicate registration
- `REGISTRY_NOT_FOUND` — lookup failed

### LLM usage
- uses_llm: no
- prompt_id: N/A

### Owner
- TODO

### Notes
- Registry is authoritative; orchestrator must query registry rather than direct discovery.


