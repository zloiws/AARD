#!/usr/bin/env python3
"""Check presence of required tables in DATABASE_URL"""
from __future__ import annotations
import os
from sqlalchemy import create_engine, inspect

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL env var")
        return 1
    engine = create_engine(db_url)
    ins = inspect(engine)
    tables = ['ollama_servers','ollama_models','agents','tools','tasks','plans','workflow_events','agent_memories','alembic_version']
    for tbl in tables:
        print(f"{tbl}: {ins.has_table(tbl)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


