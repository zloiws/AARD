#!/usr/bin/env python3
"""Run Alembic migrations programmatically and provide an idempotent DB init entrypoint."""
from __future__ import annotations

import os
import sys

from alembic import command
from alembic.config import Config


def run_alembic_upgrade():
    backend_dir = os.path.join(os.path.dirname(__file__), "..")
    # Resolve alembic script location relative to project
    script_location = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic"))
    cfg = Config(os.path.join(script_location, "alembic.ini")) if os.path.exists(os.path.join(script_location, "alembic.ini")) else Config()
    cfg.set_main_option("script_location", script_location)
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        cfg.set_main_option("sqlalchemy.url", db_url)
    try:
        command.upgrade(cfg, "heads")
        print("Alembic upgrade completed (if alembic configured and DB reachable).", file=sys.stdout)
    except Exception as exc:
        print("Alembic upgrade failed:", exc, file=sys.stderr)
        raise

def main():
    run_alembic_upgrade()

if __name__ == "__main__":
    main()


