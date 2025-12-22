#!/usr/bin/env python3
import os

from sqlalchemy import create_engine, text


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("No DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT to_regclass('public.project_metrics')")).fetchone()
        print('project_metrics exists:', res[0] is not None, '->', res[0])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


