"""Compare tables created by migrations vs models"""
import os
import sys
import re
from pathlib import Path
from collections import defaultdict

# Add parent directory to path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Load environment variables
from dotenv import load_dotenv
env_file = BASE_DIR / ".env"
load_dotenv(env_file, override=True)

from sqlalchemy import create_engine, text
from app.core.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    # Get existing tables
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """))
        existing_tables = {row[0] for row in result}
    
    # Get tables from migrations
    migrations_dir = Path(__file__).parent / "alembic" / "versions"
    migration_files = sorted([f for f in migrations_dir.glob("*.py") if f.name != "__init__.py"])
    
    tables_in_migrations = defaultdict(list)
    for mig_file in migration_files:
        with open(mig_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find create_table calls - handle both single and multi-line
            # Pattern 1: op.create_table('table_name',
            # Pattern 2: op.create_table("table_name",
            # Pattern 3: op.create_table('table_name', ...)
            create_tables = re.findall(r'op\.create_table\(\s*[\'"]([^\'"]+)[\'"]', content, re.MULTILINE)
            for table in create_tables:
                tables_in_migrations[table].append(mig_file.name)
    
    # Get tables from models
    models_dir = Path(__file__).parent / "app" / "models"
    tables_in_models = set()
    for model_file in models_dir.glob("*.py"):
        if model_file.name == "__init__.py":
            continue
        with open(model_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Find __tablename__ assignments
            tablenames = re.findall(r'__tablename__\s*=\s*["\']([^"\']+)["\']', content)
            tables_in_models.update(tablenames)
    
    print("=== ANALYSIS ===\n")
    
    print("Tables in MIGRATIONS:")
    migration_tables = set(tables_in_migrations.keys())
    for table in sorted(migration_tables):
        migs = tables_in_migrations[table]
        exists = "✓" if table in existing_tables else "✗"
        print(f"  {exists} {table} (in: {', '.join(migs)})")
    
    print(f"\nTables in MODELS:")
    for table in sorted(tables_in_models):
        exists = "✓" if table in existing_tables else "✗"
        in_mig = "✓" if table in migration_tables else "✗"
        print(f"  {exists} {table} (in migration: {in_mig})")
    
    print(f"\n=== SUMMARY ===")
    print(f"Tables in migrations: {len(migration_tables)}")
    print(f"Tables in models: {len(tables_in_models)}")
    print(f"Tables in database: {len(existing_tables)}")
    
    # Find discrepancies
    only_in_migrations = migration_tables - tables_in_models
    only_in_models = tables_in_models - migration_tables
    missing_from_db = (migration_tables | tables_in_models) - existing_tables
    extra_in_db = existing_tables - (migration_tables | tables_in_models)
    
    if only_in_migrations:
        print(f"\n⚠ Tables only in migrations (not in models): {only_in_migrations}")
    if only_in_models:
        print(f"\n⚠ Tables only in models (not in migrations): {only_in_models}")
    if missing_from_db:
        print(f"\n⚠ Tables missing from database: {missing_from_db}")
    if extra_in_db:
        print(f"\n⚠ Extra tables in database: {extra_in_db}")
    
    # Check for name mismatches
    print(f"\n=== NAME MISMATCHES ===")
    # Common patterns
    name_variations = {
        'traces': 'execution_traces',
        'agent_memory': 'agent_memories',
        'memory': 'memory_entries',
    }
    
    for old_name, new_name in name_variations.items():
        old_exists = old_name in migration_tables or old_name in tables_in_models
        new_exists = new_name in existing_tables
        if old_exists and new_exists:
            print(f"  ⚠ Name change: {old_name} -> {new_name}")

