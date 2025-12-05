"""Analyze why tables were missing and check for duplicates"""
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

from sqlalchemy import create_engine, text
from app.core.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Get all tables
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """))
        existing_tables = [row[0] for row in result]
        
        print("=== EXISTING TABLES ===")
        for table in existing_tables:
            print(f"  {table}")
        print(f"\nTotal: {len(existing_tables)} tables\n")
        
        # Check for duplicates (similar names)
        print("=== CHECKING FOR SIMILAR NAMES ===")
        similar_groups = {}
        for table in existing_tables:
            base_name = table.rstrip('s')  # Remove plural
            if base_name not in similar_groups:
                similar_groups[base_name] = []
            similar_groups[base_name].append(table)
        
        duplicates = {k: v for k, v in similar_groups.items() if len(v) > 1}
        if duplicates:
            print("⚠ Found potential duplicates:")
            for base, tables in duplicates.items():
                print(f"  {base}: {tables}")
        else:
            print("✓ No obvious duplicates found\n")
        
        # Check alembic version
        print("=== ALEMBIC VERSION ===")
        try:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()
            print(f"Current version: {version}")
        except Exception as e:
            print(f"Error: {e}")
        
        # Check which migration files exist
        print("\n=== MIGRATION FILES ===")
        migrations_dir = Path(__file__).parent / "alembic" / "versions"
        migration_files = sorted([f for f in migrations_dir.glob("*.py") if f.name != "__init__.py"])
        print(f"Found {len(migration_files)} migration files:")
        for f in migration_files:
            print(f"  {f.name}")
        
        # Check what tables should be created by each migration
        print("\n=== TABLES IN MIGRATIONS ===")
        tables_in_migrations = {}
        for mig_file in migration_files:
            with open(mig_file, 'r') as f:
                content = f.read()
                # Find create_table calls
                import re
                create_tables = re.findall(r"op\.create_table\(['\"]([^'\"]+)['\"]", content)
                if create_tables:
                    tables_in_migrations[mig_file.name] = create_tables
        
        for mig, tables in tables_in_migrations.items():
            print(f"\n{mig}:")
            for table in tables:
                exists = "✓" if table in existing_tables else "✗"
                print(f"  {exists} {table}")

