"""
Script to run Alembic migrations, handling local alembic folder conflict
"""
import sys
import os
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
    from alembic.config import Config
    from alembic import command
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
    
    # Upgrade to head
    command.upgrade(alembic_cfg, "head")
    
    print("\n✅ Migrations applied successfully!")
    
except Exception as e:
    print(f"❌ Error applying migrations: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

