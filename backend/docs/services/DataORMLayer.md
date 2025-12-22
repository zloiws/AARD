# Service: Data / ORM Layer

Role: Domain models and persistence (SQLAlchemy models + migrations).

## Contract

### Inputs
- DB connection URL, migrations, service calls operating on models

### Outputs
- Persisted domain entities, query results, applied migrations

### Errors
- `MIGRATION_ERROR` — failed migration
- `DB_CONSTRAINT_VIOLATION` — constraint failure

### LLM usage
- uses_llm: no
- prompt_id: N/A

### Owner
- TODO

### Notes
- Migrations must be idempotent and follow runbook in `docs/roadmap/migration_runbook.md`.


