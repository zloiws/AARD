#!/usr/bin/env python3
# Alter plans table column types to match SQLAlchemy models (idempotent).
from sqlalchemy import create_engine, text
import os, sys

SQL = [
    "ALTER TABLE plans ALTER COLUMN version TYPE INTEGER USING (version::integer);",
    "ALTER TABLE plans ALTER COLUMN version SET DEFAULT 1;",
    "ALTER TABLE plans ALTER COLUMN steps TYPE JSONB USING (steps::jsonb);",
    "ALTER TABLE plans ALTER COLUMN strategy TYPE JSONB USING (strategy::jsonb);",
    "ALTER TABLE plans ALTER COLUMN alternatives TYPE JSONB USING (alternatives::jsonb);",
    "ALTER TABLE plans ALTER COLUMN current_step TYPE INTEGER USING (current_step::integer);",
    "ALTER TABLE plans ALTER COLUMN estimated_duration TYPE INTEGER USING (estimated_duration::integer);",
    "ALTER TABLE plans ALTER COLUMN actual_duration TYPE INTEGER USING (actual_duration::integer);",
    "ALTER TABLE plans ALTER COLUMN current_step SET DEFAULT 0;",
]

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.begin() as conn:
        for stmt in SQL:
            try:
                conn.execute(text(stmt))
                print("Executed:", stmt)
            except Exception as e:
                print("Skipped/failed:", stmt, "->", e)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


