"""
Idempotent helper to ensure pgvector extension and `agent_memories.embedding` column exist.
Run: python -u backend/scripts/ensure_pgvector_and_embedding.py
"""
import os
import sys
from sqlalchemy import text

# Ensure repo root on path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.core.database import engine


def main():
    print("Ensure: starting pgvector + embedding check")
    if getattr(engine.dialect, "name", "") != "postgresql":
        print("Ensure: not postgresql, skipping (dialect=%s)" % getattr(engine.dialect, "name", "unknown"))
        return

    with engine.connect() as conn:
        try:
            print("Ensure: creating extension vector if not exists")
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        except Exception as e:
            print("Ensure: could not create extension:", e)

        # Check column existence and type
        try:
            col = conn.execute(text(
                "SELECT udt_name FROM information_schema.columns WHERE table_name='agent_memories' AND column_name='embedding' LIMIT 1"
            )).scalar()
            if not col:
                print("Ensure: embedding column not present, adding as type vector")
                conn.execute(text("ALTER TABLE agent_memories ADD COLUMN IF NOT EXISTS embedding vector;"))
            else:
                print(f"Ensure: embedding column exists with udt_name={col}")
                if col != 'vector':
                    print("Ensure: embedding column not 'vector' type. Consider migration to 'vector' for pgvector operations.")
        except Exception as e:
            print("Ensure: error checking/adding embedding column:", e)

    print("Ensure: done")


if __name__ == "__main__":
    main()


