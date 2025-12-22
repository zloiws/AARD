# Service: Security / Auth / Permissions

Role: Authentication and authorization utilities for API and services.

## Contract

### Inputs
- Credentials, tokens, request context

### Outputs
- Authenticated principal, permission decisions

### Errors
- `UNAUTHORIZED` — missing/invalid credentials
- `FORBIDDEN` — insufficient permissions

### LLM usage
- uses_llm: no
- prompt_id: N/A

### Owner
- TODO

### Notes
- Verify that all public endpoints are protected per policy.


