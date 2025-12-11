# Meta API

Endpoints:

- GET `/api/meta/components`  
  Returns components (artifacts/agents) with basic version information and metadata.

- GET `/api/meta/evolution-timeline`  
  Returns the evolution timeline (chronological EvolutionHistory entries).

- GET `/api/meta/components/{component_id}/diff/{version_a}/{version_b}`  
  Returns a diff between two versions (not implemented).

- POST `/api/meta/components/{component_id}/rollback/{version}`  
  Request rollback of a component to a previous version (placeholder).

Notes:
- Endpoints are intentionally minimal — full implementations should add RBAC, diff generation and rollback safety checks.


