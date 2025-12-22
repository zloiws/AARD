#!/usr/bin/env python3
"""Apply tasks.id -> UUID patch."""
from __future__ import annotations

import os
import sys
from pathlib import Path

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "patch_tasks_id_to_uuid.sql"

def load_sql():
    return SQL_PATH.read_text(encoding="utf-8")

def apply_with_sqlalchemy(sql: str):
    try:
        from sqlalchemy import create_engine
    except Exception as exc:
        print("SQLAlchemy not available:", exc, file=sys.stderr)
        return False
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL env var", file=sys.stderr)
        return False
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
    print("Applied tasks id->uuid patch via SQLAlchemy.")
    return True

def main():
    sql = load_sql()
    if apply_with_sqlalchemy(sql):
        return 0
    print("Failed to apply patch: ensure DATABASE_URL and SQLAlchemy available", file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())


