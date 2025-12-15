#!/usr/bin/env python3
"""List ollama servers and models from the configured DATABASE_URL"""
from __future__ import annotations
import os
from sqlalchemy import create_engine, text

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL env var")
        return 2
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("Servers:")
        for row in conn.execute(text("SELECT id, name, url, is_active FROM ollama_servers")).fetchall():
            print(row)
        print("\\nModels:")
        for row in conn.execute(text("SELECT id, server_id, model_name, name, is_active, capabilities FROM ollama_models")).fetchall():
            print(row)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())


