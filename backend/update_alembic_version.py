"""Update alembic_version to match the latest migration"""
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
        # Get the latest migration from files
        migrations_dir = Path(__file__).parent / "alembic" / "versions"
        migration_files = sorted([f for f in migrations_dir.glob("*.py") if f.name != "__init__.py"])
        
        if migration_files:
            # Extract revision from the last migration file
            last_migration = migration_files[-1]
            # Read first few lines to get revision
            with open(last_migration, 'r') as f:
                for line in f:
                    if 'revision' in line and '=' in line:
                        revision = line.split('=')[1].strip().strip("'")
                        break
            
            # Update alembic_version
            try:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                current = result.scalar()
                print(f"Current version: {current}")
            except:
                # Create alembic_version table if it doesn't exist
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS alembic_version (
                        version_num VARCHAR(32) NOT NULL PRIMARY KEY
                    );
                """))
                print("Created alembic_version table")
            
            # Update to latest
            conn.execute(text(f"""
                DELETE FROM alembic_version;
                INSERT INTO alembic_version (version_num) VALUES ('{revision}');
            """))
            conn.commit()
            print(f"✓ Updated alembic_version to: {revision}")
        else:
            print("No migration files found")

