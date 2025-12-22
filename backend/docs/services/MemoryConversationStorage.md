# Service: Memory / Conversation Storage

Role: Storage and retrieval of agent memory and chat sessions.

## Contract

### Inputs
- Messages, session identifiers, memory write requests

### Outputs
- Memory records, conversation context retrieval APIs

### Errors
- `MEMORY_NOT_FOUND` — requested memory missing
- `MEMORY_WRITE_ERROR` — failure persisting memory

### LLM usage
- uses_llm: no
- prompt_id: N/A

### Owner
- TODO

### Notes
- Must implement PII redaction and retention policies.


