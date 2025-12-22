#!/usr/bin/env python3
"""
Backup alembic_version rows into alembic_version_backup (idempotent).
"""
import os
import sys

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL") or "postgresql://postgres:Cdthrf12@10.39.0.101:5432/aard"

def main():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        # Ensure backup table exists
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS alembic_version_backup (
            version_num TEXT NOT NULL,
            backed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """))
        # Read current alembic_version rows (supports classic and script versions)
        try:
            res = conn.execute(text("SELECT version_num FROM alembic_version"))
            rows = res.fetchall()
        except Exception as e:
            print("No alembic_version table or error reading it:", e)
            rows = []
        if rows:
            for r in rows:
                vn = r[0]
                conn.execute(text("INSERT INTO alembic_version_backup (version_num) VALUES (:vn)"), {"vn": vn})
            print(f"Backed up {len(rows)} alembic_version rows")
        else:
            print("No rows found in alembic_version to backup")

if __name__ == '__main__':
    main()


