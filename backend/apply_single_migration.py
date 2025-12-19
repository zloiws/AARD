"""
Apply only the new migration 030 for system_parameters and uncertainty_parameters
"""
import os
import sys
from pathlib import Path

# Remove local alembic folder from path
BACKEND_DIR = Path(__file__).resolve().parent
alembic_local = BACKEND_DIR / "alembic"
if str(alembic_local) in sys.path:
    sys.path.remove(str(alembic_local))
if str(BACKEND_DIR) in sys.path:
    sys.path.remove(str(BACKEND_DIR))

from alembic import command
from alembic.config import Config

os.chdir(BACKEND_DIR)

try:
    alembic_cfg = Config("alembic.ini")
    
    print("Applying migration 030 (system_parameters and uncertainty_parameters)...")
    
    # Apply only migration 030
    command.upgrade(alembic_cfg, "030")
    
    print("\n✅ Migration 030 applied successfully!")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

