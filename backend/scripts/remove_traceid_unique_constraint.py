#!/usr/bin/env python3
from sqlalchemy import create_engine, text
import os

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    stmts = [
        "ALTER TABLE IF EXISTS execution_traces DROP CONSTRAINT IF EXISTS execution_traces_trace_id_key;",
        "DROP INDEX IF EXISTS execution_traces_trace_id_key;",
    ]
    with engine.begin() as conn:
        for s in stmts:
            try:
                conn.execute(text(s))
                print("Executed:", s)
            except Exception as e:
                print("Skipped/failed:", s, "->", e)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


