"""
Automatically restore all missing tables preserving existing data
"""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

env_file = PROJECT_ROOT / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

from app.core.database import Base, engine
from app.models import *  # Import all models
from sqlalchemy import inspect

print("=" * 70)
print(" Restoring All Missing Tables")
print("=" * 70)

# Check existing tables
inspector = inspect(engine)
existing_tables = set(inspector.get_table_names())
expected_tables = set(Base.metadata.tables.keys())
expected_tables.discard('alembic_version')
missing_tables = expected_tables - existing_tables

if not missing_tables:
    print("\n✅ All tables already exist!")
    sys.exit(0)

print(f"\nMissing {len(missing_tables)} tables. Creating...")

# Create all missing tables at once
Base.metadata.create_all(bind=engine)

# Verify
inspector = inspect(engine)
new_tables = set(inspector.get_table_names())
new_tables.discard('alembic_version')
created = new_tables - existing_tables

print(f"\n✅ Created {len(created)} tables:")
for table in sorted(created):
    print(f"   ✓ {table}")

print(f"\n✅ Total tables: {len(new_tables)}")
print("=" * 70)

