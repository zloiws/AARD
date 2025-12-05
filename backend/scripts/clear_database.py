"""
Clear all data from database
"""
import sys
import argparse
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal, engine, Base
from sqlalchemy import text
from app.core.logging_config import LoggingConfig

logger = LoggingConfig.get_logger(__name__)


def clear_database():
    """Clear all data from database tables"""
    print("=" * 70)
    print(" Clearing Database")
    print("=" * 70 + "\n")
    
    db = SessionLocal()
    
    try:
        # Get all table names
        with engine.connect() as conn:
            # Get all tables
            result = conn.execute(text("""
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """))
            tables = [row[0] for row in result]
        
        print(f"Found {len(tables)} tables to clear\n")
        
        # Disable foreign key checks temporarily
        with engine.begin() as conn:
            # Disable triggers and constraints
            conn.execute(text("SET session_replication_role = 'replica';"))
            
            # Clear each table (skip alembic_version to keep migration state)
            for table in tables:
                if table == 'alembic_version':
                    print(f"⏭️  Skipped table: {table} (keeping migration state)")
                    continue
                try:
                    conn.execute(text(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;'))
                    print(f"✅ Cleared table: {table}")
                except Exception as e:
                    print(f"⚠️  Warning clearing {table}: {e}")
            
            # Re-enable triggers and constraints
            conn.execute(text("SET session_replication_role = 'origin';"))
        
        print("\n" + "=" * 70)
        print(" ✅ Database cleared successfully!")
        print("=" * 70 + "\n")
        
        # Restore database (tables, servers, prompts)
        print("Restoring database (tables, servers, initial prompts)...")
        try:
            from scripts.restore_after_clear import main as restore_main
            restore_main()
        except Exception as e:
            print(f"⚠️  Warning: Failed to restore database: {e}")
            print("   You can manually restore by running: python scripts/restore_after_clear.py")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error clearing database: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clear all data from database")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    if not args.yes:
        print("\n⚠️  WARNING: This will delete ALL data from the database!")
        print("Press Ctrl+C to cancel, or Enter to continue...")
        
        try:
            input()
        except KeyboardInterrupt:
            print("\n❌ Cancelled.")
            sys.exit(1)
    else:
        print("\n⚠️  WARNING: Clearing ALL data from the database...")
    
    success = clear_database()
    sys.exit(0 if success else 1)

