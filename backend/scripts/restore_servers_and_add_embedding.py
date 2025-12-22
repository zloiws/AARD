"""
Restore Ollama servers/models from settings and add embedding column to memories.
Idempotent: safe to run multiple times.
"""
import sys
from pathlib import Path

from sqlalchemy import text

# ensure backend on path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.core.database import get_engine


def ensure_vector_extension(conn):
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
        return True
    except Exception:
        return False

def insert_server_and_model(conn, server_url, model_name, server_display=None):
    # Insert server if not exists
    server_row = conn.execute(
        text("SELECT id FROM ollama_servers WHERE url = :url"),
        {"url": server_url}
    ).fetchone()
    if server_row:
        server_id = server_row[0]
        print(f"Server already exists: {server_url} -> {server_id}")
    else:
        res = conn.execute(
            text("INSERT INTO ollama_servers (id, name, url, api_version, is_active, is_default) "
                 "VALUES (gen_random_uuid(), :name, :url, 'v1', true, false) RETURNING id"),
            {"name": server_display or server_url, "url": server_url}
        )
        server_id = res.fetchone()[0]
        conn.commit()
        print(f"Inserted server {server_url} -> {server_id}")

    # Insert model if provided
    if model_name:
        mrow = conn.execute(
            text("SELECT id FROM ollama_models WHERE server_id = :sid AND model_name = :m"),
            {"sid": server_id, "m": model_name}
        ).fetchone()
        if mrow:
            print(f"Model already exists: {model_name} on {server_url}")
        else:
            conn.execute(
                text("INSERT INTO ollama_models (id, server_id, name, model_name, is_active) "
                     "VALUES (gen_random_uuid(), :sid, :name, :m, true)"),
                {"sid": server_id, "name": model_name, "m": model_name}
            )
            conn.commit()
            print(f"Inserted model {model_name} for server {server_url}")

def add_embedding_column(conn, use_vector: bool):
    # Add column to agent_memories
    if use_vector:
        conn.execute(text("ALTER TABLE IF EXISTS agent_memories ADD COLUMN IF NOT EXISTS embedding vector(768);"))
    else:
        conn.execute(text("ALTER TABLE IF EXISTS agent_memories ADD COLUMN IF NOT EXISTS embedding FLOAT[];"))
    conn.commit()
    print(f"Ensured embedding column on agent_memories as {'vector' if use_vector else 'float[]'}")

def main():
    settings = get_settings()
    engine = get_engine()
    with engine.connect() as conn:
        vec_ok = ensure_vector_extension(conn)
        print("vector extension available:", vec_ok)

        # Restore servers/models from settings (two instances)
        try:
            if getattr(settings, "ollama_url_1", None):
                insert_server_and_model(conn, settings.ollama_url_1, getattr(settings, "ollama_model_1", None), "ollama_1")
            if getattr(settings, "ollama_url_2", None):
                insert_server_and_model(conn, settings.ollama_url_2, getattr(settings, "ollama_model_2", None), "ollama_2")
        except Exception as e:
            print("Failed to insert servers/models:", e)

        # Add embedding column
        try:
            add_embedding_column(conn, use_vector=vec_ok)
        except Exception as e:
            print("Failed to add embedding column:", e)

if __name__ == "__main__":
    main()


