#!/usr/bin/env python3
"""Apply SQL patch to add missing task columns."""
from __future__ import annotations
import os
import sys
from pathlib import Path

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "patch_tasks_add_columns.sql"

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
    print("Applied tasks patch via SQLAlchemy.")
    return True

def apply_with_psycopg2(sql: str):
    try:
        import psycopg2
    except Exception as exc:
        print("psycopg2 not available:", exc, file=sys.stderr)
        return False
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL env var", file=sys.stderr)
        return False
    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
    finally:
        conn.close()
    print("Applied tasks patch via psycopg2.")
    return True

def main():
    sql = load_sql()
    if apply_with_sqlalchemy(sql):
        return 0
    if apply_with_psycopg2(sql):
        return 0
    print("Failed to apply patch: install SQLAlchemy or psycopg2 and set DATABASE_URL", file=sys.stderr)
    return 2

if __name__ == "__main__":
    raise SystemExit(main())


