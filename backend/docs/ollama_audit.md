# Ollama Integration Audit

This document summarizes responsibilities, overlaps and refactor recommendations for Ollama-related modules.

## Files inspected
- `app/core/ollama_client.py`
- `app/core/ollama_db_client.py`
- `app/core/ollama_manager.py`
- `app/services/ollama_service.py`

## Responsibilities (recommended)
- `ollama_client.py` — low-level HTTP client that wraps Ollama REST API; handles requests, retries, basic auth.
- `ollama_db_client.py` — persistence helper for storing model/server metadata and embeddings in DB.
- `ollama_manager.py` — higher-level manager for pools, selection and health-checking of Ollama instances.
- `ollama_service.py` — service-layer wrapper exposing domain operations (e.g., request model inference as a service to other modules).

## Observed overlaps / duplicates
- Some helper functions for URL building, retry logic and response parsing are duplicated across `ollama_client.py` and `ollama_manager.py`.\n
- Initialization/config parsing occurs in multiple files; centralize in `app.core.config` or a single helper.

## Test coverage gaps
- Missing unit tests for edge cases (retries, rate limits) in `app/core/ollama_client.py`.\n
- `ollama_db_client.py` lacks tests for DB error handling.

## Recommendations
1. Create `app/core/ollama_utils.py` for shared helpers (URL building, common exceptions, response parsing). Move duplicated helpers there.\n2. Keep `ollama_client.py` focused on HTTP transport and `ollama_db_client.py` focused on persistence. `ollama_manager.py` coordinates multiple clients.\n3. Add unit tests for transport edge cases and persistence error handling.\n4. Add contract docs in `backend/docs/services/ToolsExternalIntegrations.md` referencing Ollama usage and prompt handling.

## Proposed follow-up PRs
- PR1: Extract helpers to `app/core/ollama_utils.py` (pure refactor with no behavior change). Include unit tests.\n- PR2: Add `ollama_client` unit tests and `ollama_db_client` tests mocking DB.\n- PR3: Small refactor in `app/services/ollama_service.py` to use `ollama_manager` for orchestration.


