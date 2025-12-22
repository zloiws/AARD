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
        sql = (
            "SELECT column_name, data_type, is_nullable, column_default "
            "FROM information_schema.columns "
            "WHERE table_name = 'plans' "
            "ORDER BY ordinal_position"
        )
        rows = conn.execute(text(sql)).fetchall()
        for r in rows:
            print(dict(r._mapping if hasattr(r, "_mapping") else r))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


