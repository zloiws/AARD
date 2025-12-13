#!/usr/bin/env python3
"""Simple script to run alembic migrations"""
import os
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Add venv site-packages to path
venv_path = Path(__file__).parent.parent / "venv" / "Lib" / "site-packages"
sys.path.insert(0, str(venv_path))

print("Python path:")
for p in sys.path[:3]:
    print(f"  {p}")

try:
    from alembic.config import Config
    from alembic import command
    from alembic.script import ScriptDirectory
    print("✅ Alembic imported successfully")

    # Create config
    cfg = Config("alembic.ini")
    print(f"Config file: {cfg.config_file_name}")

    # Check current state
    script = ScriptDirectory.from_config(cfg)
    print(f"Current heads: {script.get_heads()}")
    print(f"Current revision: {script.get_current_head()}")

    # Check database state
    from alembic.migration import MigrationContext
    from sqlalchemy import create_engine

    engine = create_engine(os.environ.get('DATABASE_URL'))
    with engine.connect() as conn:
        context = MigrationContext.configure(conn)
        current_rev = context.get_current_revision()
        print(f"Database current revision: {current_rev}")

    # Run upgrade
    print("Running alembic upgrade head...")
    command.upgrade(cfg, "head")
    print("✅ Migration completed successfully!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Migration error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
