#!/usr/bin/env python3
"""Create migration for timezone-aware datetime columns"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Add venv site-packages to path
venv_path = Path(__file__).parent.parent / "venv" / "Lib" / "site-packages"
sys.path.insert(0, str(venv_path))

def create_migration():
    """Create a new migration file for timezone datetime support"""
    from alembic.config import Config
    from alembic import command

    # Create config
    cfg = Config("alembic.ini")

    # Generate revision
    command.revision(cfg, message="Add timezone support to datetime columns", autogenerate=True)

    print("Migration created successfully!")

if __name__ == "__main__":
    create_migration()
