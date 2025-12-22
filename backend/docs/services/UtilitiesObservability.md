# Service: Utilities / Observability

Role: Logging, metrics, tracing and helper utilities.

## Contract

### Inputs
- Runtime events, traces, logs, metrics data

### Outputs
- Exported traces, metrics, logs, dashboards

### Errors
- `EXPORT_ERROR` — failed to export traces/metrics

### LLM usage
- uses_llm: no
- prompt_id: N/A

### Owner
- TODO

### Notes
- Events must include component_role, prompt_id/version (if applicable), and reason_code.


