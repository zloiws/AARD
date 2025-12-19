#!/usr/bin/env bash
set -euo pipefail

# Full backend test runner (real DB + real LLM). Place this in backend/ and run from repo root:
#   cd backend
#   cp env_full.template .env    # edit values if needed
#   ./run_full_backend_tests.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Load .env if present
if [ -f .env ]; then
  # Export non-comment, non-empty variables
  set -o allexport
  # shellcheck disable=SC1091
  source .env
  set +o allexport
fi

echo "[run_full_backend_tests] Bringing up test Postgres (docker-compose.test.yml)"
docker-compose -f docker-compose.test.yml up -d db

echo "[run_full_backend_tests] Waiting for DB to be ready..."
# Wait up to ~120 seconds
for i in $(seq 1 120); do
  DB_CONTAINER_ID=$(docker-compose -f docker-compose.test.yml ps -q db || true)
  if [ -n "${DB_CONTAINER_ID:-}" ]; then
    docker exec "${DB_CONTAINER_ID}" pg_isready -U "${POSTGRES_USER:-test_user}" >/dev/null 2>&1 && break
  fi
  sleep 1
done

echo "[run_full_backend_tests] Running Alembic migrations"
python run_migration.py

echo "[run_full_backend_tests] Seeding canonical prompts (best-effort)"
python scripts/seed_prompts_from_disk.py || true

if [ "${SEED_OLLAMA_SERVERS:-0}" = "1" ]; then
  echo "[run_full_backend_tests] Seeding Ollama servers into DB (best-effort)"
  python scripts/seed_ollama_servers.py || true
fi

echo "[run_full_backend_tests] Running full pytest suite (this will run integration + real_llm tests)"
# Run pytest and capture exit code but still perform cleanup
pytest -q
PYTEST_EXIT_CODE=$?

echo "[run_full_backend_tests] Bringing down docker-compose services"
docker-compose -f docker-compose.test.yml down

exit ${PYTEST_EXIT_CODE}


