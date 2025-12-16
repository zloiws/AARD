#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PY="$PROJECT_ROOT/venv/bin/python"

if [ ! -x "$PY" ]; then
  echo "venv python not found at $PY. Create venv first." >&2
  exit 2
fi

# Ensure alembic is available
"$PY" -m pip install --quiet alembic

# Run alembic with forwarded args
"$PY" -m alembic "$@"


