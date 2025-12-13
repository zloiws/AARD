#!/usr/bin/env python3
"""Create missing tables that are causing test failures"""
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

# Set PYTHONPATH
os.environ['PYTHONPATH'] = str(BASE_DIR / "backend")

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.engine.reflection import Inspector

# Import the missing models
from app.models.checkpoint import Checkpoint
from app.models.approval import ApprovalRequest
from app.models.evolution import EvolutionHistory, Feedback

def create_missing_tables():
    """Create only the missing tables"""
    from app.core.database import engine

    print("Creating missing tables...")

    # Create metadata for missing tables
    metadata = MetaData()

    # Add missing tables to metadata
    Checkpoint.__table__.to_metadata(metadata)
    ApprovalRequest.__table__.to_metadata(metadata)
    EvolutionHistory.__table__.to_metadata(metadata)
    Feedback.__table__.to_metadata(metadata)

    # Create only the missing tables
    try:
        metadata.create_all(bind=engine, checkfirst=True)
        print("✅ Missing tables created successfully!")

        # Verify
        inspector = Inspector.from_engine(engine)
        tables = inspector.get_table_names()
        missing_tables = ['checkpoints', 'approval_requests', 'evolution_history', 'feedback']
        created = [table for table in missing_tables if table in tables]

        print(f"Created tables: {created}")
        if len(created) == len(missing_tables):
            print("✅ All missing tables created!")
        else:
            print(f"❌ Some tables may still be missing: {[t for t in missing_tables if t not in created]}")

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    success = create_missing_tables()
    sys.exit(0 if success else 1)
