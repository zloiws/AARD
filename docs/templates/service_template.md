# Service Documentation Template

Use this template for documenting any service in AARD. Place the completed document under `docs/services/<service_name>.md`.

## Header
- **service_name**: Short canonical name (e.g., InterpretationService)
- **owner**: team/person (email)
- **one_line_role**: Single sentence describing the service responsibility

## 1. Overview
Short description, responsibilities, and context within AARD (which stage(s) it belongs to).

## 2. Service API (external)
- **Protocol**: HTTP / gRPC / internal call
- **Endpoint(s)**:
  - path, method, brief purpose
- **Request schema**: reference to JSON Schema / Pydantic model
- **Response schema**: reference to JSON Schema / Pydantic model
- **Error codes**: list and semantics
- **Authentication**: requirements or "none"

## 3. Module / Internal API
Document public classes/functions used by other modules:
- Class/Function signatures
- DTOs (Input/Output Pydantic models)
- Side effects and state changes (explicit)

## 4. LLM usage (if applicable)
- **uses_llm**: true/false
- **component_role**: canonical role (e.g., interpretation)
- **system_prompt_key**: e.g., `interpretation.system`
- **prompt_id/prompt_version**: reference or "TBD"
- **model_type**: Reasoning | Code
- **expected_output_format**: JSON schema or description
- **safety/limits**: max tokens, deterministic settings, validation steps

## 5. Events emitted / Observability
- List of WorkflowEvents / ExecutionEvents emitted with:
  - event_type
  - component_role
  - decision_source possibilities
  - minimal payload schema (input_summary, output_summary, reason_code)

## 6. Guarantees and Invariants
- Idempotency
- Concurrency behavior
- Error handling semantics and retries

## 7. Migration / Backwards compatibility notes
- Data model changes
- Required migrations

## 8. Tests & Validation
- Unit tests to add/maintain
- Integration tests required (end-to-end scenarios)

## 9. Example
Provide minimal request/response examples (JSON).

## 10. References
- Link to `docs/context/ARCHITECTURE_LAW.md`
- Link to prompts on disk: `prompts/components/`


