"""
Script to apply Alembic migrations
Run from project root: python apply_migrations.py
"""
import os
import sys
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Add venv to path if it exists
venv_site_packages = PROJECT_ROOT / "venv" / "Lib" / "site-packages"
if venv_site_packages.exists():
    sys.path.insert(0, str(venv_site_packages))

# Change to backend directory
os.chdir(BACKEND_DIR)

try:
    from alembic import command
    from alembic.config import Config

    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    print("Applying Alembic migrations...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Alembic config: {alembic_cfg.get_main_option('script_location')}")
    
    # Upgrade to head
    command.upgrade(alembic_cfg, "head")
    
    print("\n✅ Migrations applied successfully!")
    
except ImportError as e:
    print(f"❌ Error: Alembic not found. Please ensure:")
    print(f"   1. Virtual environment is activated")
    print(f"   2. Alembic is installed: pip install alembic")
    print(f"   Details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error applying migrations: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

