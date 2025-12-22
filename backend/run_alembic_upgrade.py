"""
Script to run Alembic migrations, handling local alembic folder conflict
"""
import os
import sys
from pathlib import Path

# Remove local alembic folder from path to avoid conflict with installed package
BACKEND_DIR = Path(__file__).resolve().parent
alembic_local = BACKEND_DIR / "alembic"
if str(alembic_local) in sys.path:
    sys.path.remove(str(alembic_local))

# Also remove backend directory if it causes issues
if str(BACKEND_DIR) in sys.path:
    sys.path.remove(str(BACKEND_DIR))

# Now import alembic from installed package
try:
    from alembic import command
    from alembic.config import Config
except ImportError as e:
    print(f"❌ Error: Alembic not installed. Please run: pip install alembic")
    print(f"   Details: {e}")
    sys.exit(1)

# Change to backend directory
os.chdir(BACKEND_DIR)

try:
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    print("Applying Alembic migrations...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Alembic config: {alembic_cfg.get_main_option('script_location')}")

    # Before applying migrations, attempt to remove test-only alembic marker '0001_initial' if present in DB.
    try:
        # Prefer using the application's configured engine if possible
        try:
            # Temporarily ensure backend package is importable
            import importlib
            import sys
            backend_dir = Path(__file__).resolve().parent
            if str(backend_dir) not in sys.path:
                sys.path.insert(0, str(backend_dir))
            try:
                from app.core.database import get_engine
                engine = get_engine()
            finally:
                # cleanup sys.path insertion if we added it
                if str(backend_dir) in sys.path and sys.path[0] == str(backend_dir):
                    sys.path.pop(0)
        except Exception:
            # Fallback to alembic config URL
            db_url = alembic_cfg.get_main_option("sqlalchemy.url")
            from sqlalchemy import create_engine
            engine = create_engine(db_url, future=True)

        # Inspect alembic_version and remove test marker if present
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                try:
                    res = conn.execute(text("SELECT version_num FROM alembic_version"))
                    rows = [r[0] for r in res.fetchall()] if res.returns_rows else []
                except Exception:
                    rows = []

                if "0001_initial" in rows:
                    print("Found '0001_initial' in alembic_version table — removing test marker.")
                    conn.execute(text("DELETE FROM alembic_version WHERE version_num = :v"), {"v": "0001_initial"})
                    conn.commit()
        except Exception as e:
            print(f"Could not inspect/clean alembic_version table: {e}")
    except Exception:
        pass

    # Try upgrading to single head; if multiple heads exist, upgrade all heads
    try:
        command.upgrade(alembic_cfg, "head")
        print("\nMigrations applied to head successfully.")
    except Exception as main_exc:
        try:
            # Try applying all heads
            print("Multiple heads detected or upgrade to single head failed, attempting to upgrade 'heads' (all heads).")
            command.upgrade(alembic_cfg, "heads")
            print("\nMigrations applied to all heads successfully.")
        except Exception as e:
            print(f"ERROR applying migrations: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

    print("\nMigrations completed.")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

