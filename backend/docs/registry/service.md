## service_registry
Type: Registry
Role: Single source of truth for agents, capabilities, versions and lifecycle.
Inputs: service descriptors, registration calls
Outputs: lookup API, registry entries, lifecycle state
LLM usage: no
Events emitted: workflow_event (registry updates)
Readiness: PASS (reason: registry APIs exist; verify uniqueness checks and lifecycle enforcement)


