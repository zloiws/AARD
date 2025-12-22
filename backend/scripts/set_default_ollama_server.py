#!/usr/bin/env python3
"""Set default Ollama server and default_model metadata for planning."""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("Set DATABASE_URL")
        return 2
    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text("UPDATE ollama_servers SET is_default = TRUE WHERE url LIKE '%10.39.0.101%';"))
        conn.execute(text("UPDATE ollama_servers SET server_metadata = COALESCE(server_metadata, '{}'::jsonb) || jsonb_build_object('default_model', 'qwen3:8b') WHERE url LIKE '%10.39.0.101%';"))
        print('Set is_default and default_model for 10.39.0.101')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())


