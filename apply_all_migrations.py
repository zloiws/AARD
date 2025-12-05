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
    
    # Check if we need to reset or just upgrade
    if current_rev and current_rev != "001":
        print(f"\n⚠️  Current revision is {current_rev}, not base (001)")
        print("   This script will reset migration state to 001 and reapply all migrations.")
        print("   ⚠️  WARNING: This may cause issues if tables already exist!")
        print("\n   Type 'RESET MIGRATIONS' to confirm (or Ctrl+C to cancel):")
        
        try:
            confirmation = input("> ").strip()
            if confirmation != "RESET MIGRATIONS":
                print(f"\n❌ Confirmation failed. Expected 'RESET MIGRATIONS', got: '{confirmation}'")
                print("   Operation cancelled.")
                print("\n   Alternative: Use 'python apply_migrations.py' to upgrade from current revision")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n❌ Cancelled.")
            sys.exit(1)
        
        try:
            # Stamp to base (001) to reset migration state
            print("\n1. Stamping database to base revision (001)...")
            print("   ⚠️  WARNING: This resets migration state but does NOT delete tables!")
            command.stamp(alembic_cfg, "001")
            print("   ✓ Stamped to 001")
        except Exception as e:
            print(f"   ❌ Failed to stamp: {e}")
            print("   Trying to upgrade from current revision instead...")
            current_rev = None  # Fall through to upgrade
    
    if not current_rev or current_rev == "001":
        # Now upgrade to head
        print("\n2. Upgrading to head (applying all migrations)...")
        try:
            command.upgrade(alembic_cfg, "head")
            print("\n✅ All migrations applied successfully!")
        except Exception as e:
            print(f"\n❌ Error applying migrations: {e}")
            print("\nThis may happen if:")
            print("  1. Tables from earlier migrations are missing")
            print("  2. Migration dependencies are broken")
            print("\nTry:")
            print("  1. Check database state: python backend/scripts/check_database_state.py")
            print("  2. Restore missing tables: python backend/scripts/restore_after_clear.py")
            raise
        
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

