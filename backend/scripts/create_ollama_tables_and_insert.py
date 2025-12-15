#!/usr/bin/env python3
"""
Create minimal ollama tables if missing and insert/activate specified servers/models.
Run from project root with venv python:
  ..\\venv\\Scripts\\python.exe -c "import sys; sys.path.insert(0, r'C:\\work\\AARD\\backend'); exec(open(r'C:\\work\\AARD\\backend\\scripts\\create_ollama_tables_and_insert.py').read())"
"""
from sqlalchemy import create_engine, text
from app.core.config import get_settings
from datetime import datetime


def main():
    settings = get_settings()
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        # Create servers table (minimal)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ollama_servers (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name TEXT UNIQUE,
                    url TEXT UNIQUE,
                    api_version TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );
                """
            )
        )

        # Create models table (minimal)
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS ollama_models (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    server_id UUID,
                    name TEXT,
                    model_name TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
                );
                """
            )
        )

        # Upsert servers
        servers = [
            {"name": "huihui_10_39_0_6", "url": "http://10.39.0.6"},
            {"name": "qwen3_10_39_0_101", "url": "http://10.39.0.101"},
        ]
        for s in servers:
            conn.execute(
                text(
                    """
                    INSERT INTO ollama_servers (name, url, api_version, is_active, created_at)
                    VALUES (:name, :url, 'v1', TRUE, :now)
                    ON CONFLICT (url) DO UPDATE SET is_active = TRUE, name = EXCLUDED.name;
                    """
                ),
                {"name": s["name"], "url": s["url"], "now": datetime.utcnow()},
            )

        # Ensure models exist and are active
        models = [
            {"server_url": "http://10.39.0.6", "name": "huihui_ai/qwen3-vl-abliterated:8b-instruct"},
            {"server_url": "http://10.39.0.101", "name": "qwen3:8b"},
        ]
        for m in models:
            # find server id
            row = conn.execute(
                text("SELECT id FROM ollama_servers WHERE url = :url"), {"url": m["server_url"]}
            ).fetchone()
            if row:
                server_id = row[0]
                conn.execute(
                    text(
                        """
                        INSERT INTO ollama_models (server_id, name, model_name, is_active, created_at)
                        VALUES (:server_id, :name, :model_name, TRUE, :now)
                        ON CONFLICT (server_id, model_name) DO UPDATE SET is_active = TRUE, name = EXCLUDED.name;
                        """
                    ),
                    {"server_id": server_id, "name": m["name"], "model_name": m["name"], "now": datetime.utcnow()},
                )

        # Print verification
        rows = conn.execute(
            text(
                "SELECT s.url AS server_url, s.is_active AS server_active, m.model_name AS model_name, m.is_active AS model_active FROM ollama_servers s LEFT JOIN ollama_models m ON m.server_id = s.id WHERE s.url IN ('http://10.39.0.6','http://10.39.0.101') OR m.model_name IN ('huihui_ai/qwen3-vl-abliterated:8b-instruct','qwen3:8b');"
            )
        ).fetchall()
        for r in rows:
            print(dict(r))


if __name__ == "__main__":
    main()


