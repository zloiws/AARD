# Service: Tools & External Integrations

Role: Adapters to external systems and execution capabilities (Ollama, web search, code execution).

## Contract

### Inputs
- Tool requests, payloads, prompts when LLM is involved

### Outputs
- Tool results, execution artifacts, errors

### Errors
- `TOOL_TIMEOUT` — external call timed out
- `TOOL_ERROR` — external tool returned failure

### LLM usage
- uses_llm: varies (tools themselves usually not LLM components)
- prompt_id: N/A or VERIFY if tool triggers an LLM

### Owner
- TODO

### Notes
- Tools are Capabilities per ARCHITECTURE_LAW.md and have strict interfaces.


