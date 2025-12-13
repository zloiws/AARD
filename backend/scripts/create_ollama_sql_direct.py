#!/usr/bin/env python3
"""
Create minimal ollama tables and activate specified servers/models using direct DB URL (no app import).
This script uses the current configured DB for tests.
"""
from sqlalchemy import create_engine, text
from datetime import datetime

# Replace with DB URL printed earlier (ensure this matches your environment)
DB_URL = "postgresql://postgres:Cdthrf12@10.39.0.101:5432/aard"

def main():
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        # Create minimal tables if missing
        conn.execute(text(
            """CREATE TABLE IF NOT EXISTS ollama_servers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT UNIQUE,
                url TEXT UNIQUE,
                api_version TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            );"""
        ))

        conn.execute(text(
            """CREATE TABLE IF NOT EXISTS ollama_models (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                server_id UUID,
                name TEXT,
                model_name TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
            );"""
        ))
        # Ensure additional columns exist on servers (idempotent)
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS auth_type TEXT;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS auth_config JSONB;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS is_default BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS description TEXT;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS capabilities JSONB;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS max_concurrent INTEGER DEFAULT 1;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMP WITH TIME ZONE;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS is_available BOOLEAN DEFAULT FALSE;"))
        conn.execute(text("ALTER TABLE ollama_servers ADD COLUMN IF NOT EXISTS server_metadata JSONB;"))

        # Ensure additional columns exist on models (idempotent)
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS server_id UUID;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS digest TEXT;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS size_bytes BIGINT;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS format TEXT;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS modified_at TIMESTAMP WITH TIME ZONE;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS details JSONB;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS capabilities JSONB;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE;"))
        conn.execute(text("ALTER TABLE ollama_models ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP WITH TIME ZONE;"))
        # Ensure unique index for upsert on (server_id, model_name)
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_ollama_models_server_model ON ollama_models(server_id, model_name);"
        ))

        # Upsert servers
        servers = [
            ("huihui_10_39_0_6", "http://10.39.0.6"),
            ("qwen3_10_39_0_101", "http://10.39.0.101"),
        ]
        for name, url in servers:
            conn.execute(text(
                """INSERT INTO ollama_servers (name, url, api_version, is_active, created_at)
                   VALUES (:name, :url, 'v1', TRUE, :now)
                   ON CONFLICT (url) DO UPDATE SET is_active = TRUE, name = EXCLUDED.name;"""), {"name": name, "url": url, "now": datetime.utcnow()})

        # Upsert models
        models = [
            ("http://10.39.0.6", "huihui_ai/qwen3-vl-abliterated:8b-instruct"),
            ("http://10.39.0.101", "qwen3:8b"),
        ]
        for server_url, model_name in models:
            row = conn.execute(text("SELECT id FROM ollama_servers WHERE url = :url"), {"url": server_url}).fetchone()
            if row:
                server_id = row[0]
                conn.execute(text(
                    """INSERT INTO ollama_models (server_id, name, model_name, is_active, created_at)
                       VALUES (:server_id, :name, :model_name, TRUE, :now)
                       ON CONFLICT (server_id, model_name) DO UPDATE SET is_active = TRUE, name = EXCLUDED.name;"""), {"server_id": server_id, "name": model_name, "model_name": model_name, "now": datetime.utcnow()})

        # Print verification
        rows = conn.execute(text(
            "SELECT s.url AS server_url, s.is_active AS server_active, m.model_name AS model_name, m.is_active AS model_active FROM ollama_servers s LEFT JOIN ollama_models m ON m.server_id = s.id WHERE s.url IN ('http://10.39.0.6','http://10.39.0.101') OR m.model_name IN ('huihui_ai/qwen3-vl-abliterated:8b-instruct','qwen3:8b');"
        )).fetchall()
        for r in rows:
            try:
                print(dict(r._mapping))
            except Exception:
                # fallback
                print(r)
        # Ensure models have planning capability for tests
        conn.execute(text("UPDATE ollama_models SET capabilities = '[]'::jsonb WHERE capabilities IS NULL;"))
        conn.execute(text("UPDATE ollama_models SET capabilities = '[\"planning\"]'::jsonb WHERE model_name IN ('huihui_ai/qwen3-vl-abliterated:8b-instruct','qwen3:8b');"))

if __name__ == "__main__":
    main()


