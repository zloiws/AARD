"""
Script to apply Alembic migrations
"""
import sys
import os
from pathlib import Path

# Import alembic BEFORE changing directory
try:
    from alembic.config import Config
    from alembic import command
except ImportError:
    # Try to add venv to path if alembic not found
    project_root = Path(__file__).resolve().parent.parent
    venv_site_packages = project_root / "venv" / "Lib" / "site-packages"
    if venv_site_packages.exists():
        sys.path.insert(0, str(venv_site_packages))
    from alembic.config import Config
    from alembic import command

# Add backend to path and change directory
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

try:
    
    # Create Alembic config
    alembic_cfg = Config("alembic.ini")
    
    print("Applying Alembic migrations...")
    print(f"Working directory: {os.getcwd()}")
    print(f"Alembic config: {alembic_cfg.get_main_option('script_location')}")
    
    # Upgrade to head
    command.upgrade(alembic_cfg, "head")
    
    print("\n✅ Migrations applied successfully!")
    
except ImportError as e:
    print(f"❌ Error: Alembic not installed. Please run: pip install alembic")
    print(f"   Details: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error applying migrations: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

