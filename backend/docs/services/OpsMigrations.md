# Service: Ops / Maintenance / Migrations

Role: CLI and scripts for schema migrations, seeding and DB maintenance.

## Contract

### Inputs
- `.env`, DB connection, migration scripts

### Outputs
- Applied migrations, status reports, seed data

### Errors
- `MIGRATION_CONFLICT` — multiple heads or conflicting DDL
- `LOCK_ERROR` — cannot obtain lock for migration

### LLM usage
- uses_llm: no
- prompt_id: N/A

### Owner
- TODO

### Notes
- Consolidate multiple migration scripts into a single CLI to avoid duplication and locking issues.


