"""
Clear all data from database

⚠️  WARNING: This script deletes ALL data from the database!
⚠️  This operation CANNOT be undone!
⚠️  Use only when explicitly needed and with proper backups!

This script requires explicit confirmation:
1. Type 'DELETE ALL DATA' (first confirmation)
2. Type 'YES' (final confirmation)
Or use --yes flag (still requires manual execution)
"""
import sys
import argparse
from pathlib import Path
from datetime import datetime

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
        
        # Restore database (tables, servers, prompts) - only if explicitly requested
        print("\n" + "=" * 70)
        print(" Restore Database?")
        print("=" * 70)
        print("Do you want to restore tables, servers, and initial prompts?")
        print("Type 'RESTORE' to restore, or press Enter to skip:")
        
        try:
            restore_choice = input("> ").strip()
            if restore_choice == "RESTORE":
                print("\nRestoring database (tables, servers, initial prompts)...")
                try:
                    from scripts.restore_after_clear import main as restore_main
                    restore_main()
                except Exception as e:
                    print(f"⚠️  Warning: Failed to restore database: {e}")
                    print("   You can manually restore by running: python scripts/restore_after_clear.py")
            else:
                print("⏭️  Skipping restoration. You can restore manually later.")
        except KeyboardInterrupt:
            print("\n⏭️  Skipping restoration.")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error clearing database: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    # Safety check: prevent accidental execution
    import os
    from app.core.config import get_settings
    
    # Check environment
    try:
        settings = get_settings()
        if settings.app_env.lower() == "production":
            print("\n❌ ERROR: Cannot clear database in PRODUCTION environment!")
            print("   This script is disabled for safety.")
            print("   If you really need to clear production database:")
            print("   1. Set APP_ENV to 'development' in .env")
            print("   2. Add --force-production flag (requires confirmation)")
            sys.exit(1)
    except:
        pass  # If config fails, continue with extra warnings
    
    parser = argparse.ArgumentParser(description="Clear all data from database")
    parser.add_argument("--yes", "-y", action="store_true", help="Skip first confirmation prompt")
    parser.add_argument("--force-production", action="store_true", help="Allow clearing in production (requires confirmation)")
    args = parser.parse_args()
    
    # Extra safety: require explicit confirmation
    if not args.yes:
        print("\n" + "=" * 70)
        print(" ⚠️  CRITICAL WARNING ⚠️")
        print("=" * 70)
        print(" This will DELETE ALL DATA from the database!")
        print(" This action CANNOT be undone!")
        print("=" * 70)
        print("\nTo confirm, type 'DELETE ALL DATA' (exactly as shown):")
        
        try:
            confirmation = input("> ").strip()
            if confirmation != "DELETE ALL DATA":
                print(f"\n❌ Confirmation failed. Expected 'DELETE ALL DATA', got: '{confirmation}'")
                print("   Operation cancelled.")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n❌ Cancelled.")
            sys.exit(1)
        
        # Second confirmation
        print("\n⚠️  Final confirmation required!")
        print("Type 'YES' to proceed (case-sensitive):")
        try:
            final_confirmation = input("> ").strip()
            if final_confirmation != "YES":
                print(f"\n❌ Final confirmation failed. Expected 'YES', got: '{final_confirmation}'")
                print("   Operation cancelled.")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n❌ Cancelled.")
            sys.exit(1)
    else:
        print("\n⚠️  WARNING: Using --yes flag, skipping interactive confirmation")
        print("⚠️  This will delete ALL data from the database!")
    
    # Log the operation
    logger.warning("DATABASE CLEAR OPERATION INITIATED", extra={
        "operation": "clear_database",
        "user_confirmation": args.yes,
        "timestamp": str(datetime.now())
    })
    
    success = clear_database()
    sys.exit(0 if success else 1)

