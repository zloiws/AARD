#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$SCRIPT_DIR/../venv/bin/python"

if [ ! -x "$VENV_PY" ]; then
  echo "venv python not found at $VENV_PY. Make sure venv exists and is activated."
  exit 1
fi

ACTION=${1:-upgrade}
ARG=${2:-head}

case "$ACTION" in
  revision)
    MESSAGE=${2:-"autogen"}
    "$VENV_PY" -m alembic revision --autogenerate -m "$MESSAGE"
    ;;
  upgrade)
    "$VENV_PY" -m alembic upgrade "$ARG"
    ;;
  current)
    "$VENV_PY" -m alembic current
    ;;
  *)
    echo "Unknown action: $ACTION"
    exit 2
    ;;
esac


