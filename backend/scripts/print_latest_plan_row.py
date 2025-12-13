#!/usr/bin/env python3
from sqlalchemy import create_engine, text
import os, json

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version, strategy, steps, current_step, estimated_duration, actual_duration FROM plans ORDER BY created_at DESC LIMIT 1")).fetchone()
        if not row:
            print("No plans")
            return 0
        try:
            m = dict(row._mapping)
        except Exception:
            m = dict(row)
        for k,v in m.items():
            print(k, "->", type(v), ":", v)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


