"""
Cleanup DB: drop all tables except a whitelist (ollama_server, ollama_model, alembic_version).
This script is destructive. It will DROP TABLE ... CASCADE for all public tables not in the whitelist.
"""
from sqlalchemy import text
from app.core.database import get_engine

WHITELIST = {"ollama_server", "ollama_model", "alembic_version"}

def main():
    engine = get_engine()
    with engine.connect() as conn:
        # collect public tables
        res = conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type='BASE TABLE';"
        )).fetchall()
        tables = [r[0] for r in res]
        to_drop = [t for t in tables if t not in WHITELIST]
        if not to_drop:
            print("No tables to drop.")
            return
        print("Dropping tables:", to_drop)
        for t in to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS public.{t} CASCADE;"))
                print(f"Dropped {t}")
            except Exception as e:
                print(f"Failed to drop {t}: {e}")
        print("Cleanup completed.")

if __name__ == "__main__":
    main()


