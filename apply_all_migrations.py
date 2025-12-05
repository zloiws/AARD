"""
Script to apply all migrations from the beginning
This will create all missing tables
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
    from sqlalchemy import create_engine, text, inspect
    from dotenv import load_dotenv
    
    # Load environment variables
    env_file = PROJECT_ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    
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
    print("Applying all migrations from the beginning")
    print("=" * 70)
    
    alembic_cfg = Config("alembic.ini")
    
    # Check current state
    engine = create_engine(db_url)
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print(f"\nCurrent tables: {len(existing_tables)}")
    print(f"Existing tables: {', '.join(sorted(existing_tables))}")
    
    # Check current revision
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            current_rev = result.scalar()
            print(f"\nCurrent revision: {current_rev}")
    except:
        print("\nNo revision found - starting from scratch")
        current_rev = None
    
    # Strategy: Stamp to base, then upgrade
    print("\nStrategy: Stamping to base revision, then upgrading...")
    
    try:
        # Stamp to base (001) to reset migration state
        print("\n1. Stamping database to base revision (001)...")
        command.stamp(alembic_cfg, "001")
        print("   ✓ Stamped to 001")
        
        # Now upgrade to head
        print("\n2. Upgrading to head (applying all migrations)...")
        command.upgrade(alembic_cfg, "head")
        print("\n✅ All migrations applied successfully!")
        
        # Verify tables
        print("\n3. Verifying tables...")
        inspector = inspect(engine)
        new_tables = inspector.get_table_names()
        print(f"   Total tables: {len(new_tables)}")
        
        required_tables = ['tasks', 'plans', 'agents', 'ollama_servers', 'ollama_models', 
                          'project_metrics', 'audit_reports', 'benchmark_tasks', 'benchmark_results']
        print("\n   Required tables:")
        for table in required_tables:
            status = "✓" if table in new_tables else "✗"
            print(f"     {status} {table}")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTrying alternative approach: upgrade from current revision...")
        try:
            command.upgrade(alembic_cfg, "head")
            print("✅ Migrations applied!")
        except Exception as e2:
            print(f"❌ Still failed: {e2}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    
    print("\n" + "=" * 70)
    
except ImportError as e:
    print(f"❌ Error: Required modules not found: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

