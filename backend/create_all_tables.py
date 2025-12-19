"""Create all missing tables using SQLAlchemy Base.metadata"""
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

from app.core.database import Base, engine
from app.models import *  # Import all models to register them

if __name__ == "__main__":
    print("Creating all tables from models...")
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("All tables created successfully!")
        
        # Verify
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nCreated {len(tables)} tables:")
        for table in sorted(tables):
            if table != 'alembic_version':
                print(f"  {table}")
                
    except Exception as e:
        print(f"Error creating tables: {e}")
        import traceback
        traceback.print_exc()

