#!/usr/bin/env python3
import os

from sqlalchemy import create_engine, text


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, version, title, created_at FROM plans ORDER BY created_at DESC LIMIT 5")).fetchall()
        if not rows:
            print("No plans found")
            return 0
        for r in rows:
            try:
                m = dict(r._mapping)
            except Exception:
                m = dict(r)
            print(m)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


