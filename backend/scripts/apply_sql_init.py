#!/usr/bin/env python3
"""Apply idempotent SQL init file to the configured database.

Usage:
  - Set DATABASE_URL env var (e.g. postgresql://user:pass@host:5432/dbname)
  - python backend/scripts/apply_sql_init.py
"""
from __future__ import annotations
import os
import sys

SQL_PATH = os.path.join(os.path.dirname(__file__), "..", "sql", "init_schema.sql")

def load_sql():
    with open(SQL_PATH, "r", encoding="utf-8") as fh:
        return fh.read()

def apply_with_sqlalchemy(sql: str):
    try:
        from sqlalchemy import create_engine, text
    except Exception as exc:
        print("SQLAlchemy not available:", exc, file=sys.stderr)
        return False
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL env var to apply SQL via SQLAlchemy.", file=sys.stderr)
        return False
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
    print("Applied SQL via SQLAlchemy.")
    return True

def apply_with_psycopg2(sql: str):
    try:
        import psycopg2
    except Exception as exc:
        print("psycopg2 not available:", exc, file=sys.stderr)
        return False
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL env var to apply SQL via psycopg2.", file=sys.stderr)
        return False
    # psycopg2 requires parsing; simple approach: use libpq connection string
    conn = psycopg2.connect(db_url)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
    finally:
        conn.close()
    print("Applied SQL via psycopg2.")
    return True

def main():
    sql = load_sql()
    # Try sqlalchemy first, then psycopg2, else print SQL for manual application
    if apply_with_sqlalchemy(sql):
        return
    if apply_with_psycopg2(sql):
        return
    print("--- SQL (apply manually with psql) ---")
    print(sql)
    print("--- End SQL ---")
    print("Install SQLAlchemy or psycopg2 and set DATABASE_URL to apply automatically.", file=sys.stderr)

if __name__ == "__main__":
    main()


