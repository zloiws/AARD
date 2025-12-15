#!/usr/bin/env python3
"""Print columns for a table using DATABASE_URL"""
from __future__ import annotations
import os
from sqlalchemy import create_engine, inspect

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL env var")
        return 2
    engine = create_engine(db_url)
    ins = inspect(engine)
    table = "workflow_events"
    cols = ins.get_columns(table)
    for c in cols:
        print(c['name'], c.get('type'))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())



