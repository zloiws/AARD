"""
Script to check database state and detect potential issues
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

# Load environment
BASE_DIR = backend_dir.parent
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE, override=True)

# Get database URL
db_url = os.getenv("DATABASE_URL")
if not db_url:
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("DB_NAME", "aard")
    db_user = os.getenv("DB_USER", "postgres")
    db_password = os.getenv("DB_PASSWORD", "")
    db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

print("=" * 70)
print(" Database State Check")
print("=" * 70)

try:
    engine = create_engine(db_url)
    inspector = inspect(engine)
    
    # Get all tables
    all_tables = inspector.get_table_names()
    
    print(f"\nTotal tables in database: {len(all_tables)}")
    print(f"Tables: {', '.join(sorted(all_tables))}")
    
    # Check expected tables
    expected_core_tables = [
        'tasks', 'plans', 'artifacts', 'ollama_servers', 'ollama_models',
        'agents', 'tools', 'prompts', 'project_metrics', 'audit_reports'
    ]
    
    print("\n" + "=" * 70)
    print(" Expected Core Tables")
    print("=" * 70)
    
    missing_tables = []
    for table in expected_core_tables:
        if table in all_tables:
            print(f"  ✓ {table}")
        else:
            print(f"  ✗ {table} - MISSING")
            missing_tables.append(table)
    
    # Check alembic version
    print("\n" + "=" * 70)
    print(" Migration State")
    print("=" * 70)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_rev = result.scalar()
            print(f"  Current revision: {current_rev}")
    except Exception as e:
        print(f"  ⚠️  Could not read migration state: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print(" Summary")
    print("=" * 70)
    
    if missing_tables:
        print(f"  ⚠️  WARNING: {len(missing_tables)} expected tables are missing!")
        print(f"  Missing: {', '.join(missing_tables)}")
        print("\n  Possible causes:")
        print("    1. Migrations were not applied from the beginning")
        print("    2. Tables were manually dropped")
        print("    3. Database was partially cleared")
        print("\n  To fix:")
        print("    1. Apply all migrations: python apply_migrations.py")
        print("    2. Or restore tables: python backend/scripts/restore_after_clear.py")
    else:
        print("  ✅ All expected tables exist")
    
    # Check for Phase 3 tables
    phase3_tables = ['project_metrics', 'audit_reports']
    print("\n  Phase 3 tables:")
    for table in phase3_tables:
        if table in all_tables:
            print(f"    ✓ {table}")
        else:
            print(f"    ✗ {table} - MISSING")
    
    print("\n" + "=" * 70)
    
except Exception as e:
    print(f"\n❌ Error checking database: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

