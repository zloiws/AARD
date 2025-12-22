# Service: Application Core

Role: Infrastructure foundation — configuration, DB, orchestration, tracing & metrics, service registry.

## Contract

### Inputs
- `env` / `.env` variables (see `app.core.config`)
- HTTP/worker requests for orchestrator

### Outputs
- `Settings` object
- SQLAlchemy `engine` and `SessionLocal`
- Registered runtime services
- Tracing spans and metrics

### Errors
- `CONFIG_ERROR` — missing/invalid environment configuration
- `DB_CONNECTION_ERROR` — cannot connect to DB

### LLM usage
- uses_llm: no
- prompt_id: N/A

### Owner
- TODO

### Notes
- Verify PromptSelector integration for components that require system prompts.


