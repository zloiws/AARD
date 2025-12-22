# InterpretationService — Service Documentation

owner: team:core-inference@example.com
service_name: InterpretationService
one_line_role: Convert raw user input into a StructuredIntent contract suitable for planning and routing.

## 1. Overview
InterpretationService produces a canonical `StructuredIntent` from free-form user input. It is a Component (uses LLM) and belongs to the `interpretation` stage.

## 2. Service API (external)
- **Protocol**: internal call via ExecutionContext / PromptManager (also exposed via `/api/interpret` for tooling)
- **Endpoint**:
  - `POST /api/interpret` — body: `InterpretRequest`, returns `InterpretResponse`

### Request (Pydantic)
```python
class InterpretationRequest(BaseModel):
    user_text: str
    session_id: Optional[str] = None
    context: Optional[dict] = None
```

### Response (Pydantic)
```python
class InterpretationResponse(BaseModel):
    structured_intent: dict  # Serialized StructuredIntent
    clarification_questions: Optional[List[str]] = None
    metadata: Optional[dict] = None
```

## 3. Module / Internal API
- Public class: `InterpretationService(db: Session)`  
- Method: `async def interpret(self, text: str, context: ExecutionContext) -> StructuredIntent`
- Input: `user_text` (string), `context.metadata` (optional)
- Output: `StructuredIntent` Pydantic model (fields: intent_type, slots, confidence, raw_llm_response)

## 4. LLM usage
- **uses_llm**: true  
- **component_role**: `interpretation`  
- **system_prompt_key**: `interpretation.system` (canonical file under `prompts/components/interpretation.system`)  
- **model_type**: Reasoning Model  
- **expected_output_format**: JSON matching StructuredIntent schema  
- **safety/limits**: low temperature (0.0–0.3), deterministic parsing, validate JSON output and fall back to legacy parser when invalid.

## 5. Events emitted / Observability
- Emits WorkflowEvent at start/complete/error with:
  - `component_role`: `interpretation`
  - `prompt_id` / `prompt_version` (if resolved)
  - `decision_source`: `component` (or `human` if clarification accepted)
  - payload: `{ "structured_intent_summary": ..., "clarification": [...], "llm_response_snippet": "..." }`

## 6. Guarantees and Invariants
- If LLM output cannot be parsed to StructuredIntent → return `clarification_required` with explicit questions (no silent failures).
- Interpretation does not change Registry or persistent state.
- Interpretation output must be deterministic for same input + prompt_id/version.

## 7. Migration / Backwards compatibility notes
- When changing StructuredIntent schema, create a migration and update `docs/services/interpretation_service.md` with version changes.

## 8. Tests & Validation
- Unit tests:
  - parse valid LLM JSON → structured intent
  - invalid JSON → fallback to legacy parser
  - clarification flow produces expected questions
- Integration:
  - end-to-end: user input → interpretation → planning receives structured_intent

## 9. Example
Request:
```json
{ "user_text": "Schedule a meeting with Alice next week about the Q4 report." }
```
Response (summary):
```json
{
  "structured_intent": {
    "intent_type": "schedule_meeting",
    "slots": { "participant": "Alice", "time": "next week", "topic": "Q4 report" },
    "confidence": 0.92
  }
}
```

## 10. References
- ARCHITECTURE_LAW.md
- prompts/components/interpretation.system
- docs/api/contracts_v0.md (ExecutionEvent schema)


