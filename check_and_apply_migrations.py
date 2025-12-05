"""
Script to check current migration state and apply missing migrations
"""
import sys
import os
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Add venv to path if it exists
venv_site_packages = PROJECT_ROOT / "venv" / "Lib" / "site-packages"
if venv_site_packages.exists():
    sys.path.insert(0, str(venv_site_packages))

# Change to backend directory
os.chdir(BACKEND_DIR)

try:
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine, text
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        # Try to construct from individual components
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME", "aard")
        db_user = os.getenv("DB_USER", "postgres")
        db_password = os.getenv("DB_PASSWORD", "")
        db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    
    print("=" * 70)
    print("Checking migration state and applying missing migrations")
    print("=" * 70)
    
    # Check current revision
    alembic_cfg = Config("alembic.ini")
    
    print("\n1. Checking current database revision...")
    try:
        # Connect to database to check alembic_version table
        engine = create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_rev = result.scalar()
            if current_rev:
                print(f"   Current revision: {current_rev}")
            else:
                print("   No migrations applied yet")
    except Exception as e:
        print(f"   Could not check current revision: {e}")
        print("   Will try to apply from beginning")
        current_rev = None
    
    # Check if required tables exist
    print("\n2. Checking for required tables...")
    required_tables = ['ollama_servers', 'ollama_models', 'tasks', 'plans']
    missing_tables = []
    
    try:
        with engine.connect() as conn:
            for table in required_tables:
                result = conn.execute(text(
                    f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}')"
                ))
                exists = result.scalar()
                if not exists:
                    missing_tables.append(table)
                    print(f"   ❌ Missing: {table}")
                else:
                    print(f"   ✓ Found: {table}")
    except Exception as e:
        print(f"   Error checking tables: {e}")
    
    # Apply migrations
    print("\n3. Applying migrations...")
    try:
        command.upgrade(alembic_cfg, "head")
        print("\n✅ Migrations applied successfully!")
    except Exception as e:
        print(f"\n❌ Error applying migrations: {e}")
        print("\nTrying to apply migrations step by step...")
        
        # Try to apply from a specific revision
        if missing_tables:
            print(f"\nMissing tables detected: {missing_tables}")
            if 'ollama_servers' in missing_tables or 'ollama_models' in missing_tables:
                print("These tables should be created by migration 002.")
                print("Trying to apply migrations starting from 002...")
                try:
                    # Stamp to revision 001 if needed
                    if not current_rev:
                        print("Stamping database to base revision...")
                        command.stamp(alembic_cfg, "001")
                    command.upgrade(alembic_cfg, "head")
                    print("\n✅ Migrations applied successfully!")
                except Exception as e2:
                    print(f"\n❌ Still failed: {e2}")
                    print("\nYou may need to:")
                    print("  1. Check if database is accessible")
                    print("  2. Apply migrations manually starting from 001")
                    print("  3. Create missing tables manually")
    
    print("\n" + "=" * 70)
    
except ImportError as e:
    print(f"❌ Error: Required modules not found: {e}")
    print("Please ensure:")
    print("  1. Virtual environment is activated")
    print("  2. Dependencies are installed: pip install -r backend/requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

