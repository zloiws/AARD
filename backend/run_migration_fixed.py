"""Run Alembic migrations with proper environment loading"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables
from dotenv import load_dotenv

env_file = BASE_DIR / ".env"
load_dotenv(env_file, override=True)

# Set working directory to backend
os.chdir(Path(__file__).resolve().parent)

if __name__ == "__main__":
    from alembic import command
    from alembic.config import Config

    # Load Alembic config
    alembic_cfg = Config("alembic.ini")
    
    # Run upgrade
    print("Applying database migrations...")
    command.upgrade(alembic_cfg, "head")
    print("✓ Migrations applied successfully!")

