# Service: Business Services

Role: Core domain logic: planning, execution, queues, metrics, artifact generation.

## Contract

### Inputs
- API/service calls, domain models, tool outputs

### Outputs
- Domain changes (Plan/Task entities), events, metrics

### Errors
- `BUSINESS_VALIDATION_ERROR` — invalid domain inputs
- `EXECUTION_FAILURE` — failure during plan execution

### LLM usage
- uses_llm: depends on component (VERIFY per sub-module)
- prompt_id: VERIFY

### Owner
- TODO

### Notes
- Each service must document Input/Output DTOs in `docs/services/<service>.md`.


