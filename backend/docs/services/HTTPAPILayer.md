# Service: HTTP API Layer

Role: Presentation layer — FastAPI handlers, validation and routing to business services.

## Contract

### Inputs
- HTTP requests (path, query, headers, body)
- Auth context (from middleware)

### Outputs
- JSON responses, status codes
- Invocations of `app.services.*` APIs

### Errors
- `BAD_REQUEST` — validation failure
- `UNAUTHORIZED` — auth failure
- `NOT_FOUND` — resource missing

### LLM usage
- uses_llm: no (handlers delegate to services/components that may use LLM)
- prompt_id: VERIFY per-service

### Owner
- TODO

### Notes
- Ensure OpenAPI contracts are up-to-date for each route.


