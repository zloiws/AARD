"""
Setup database and run Phase 6 real tests
"""
import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.database import SessionLocal, engine
from app.core.logging_config import LoggingConfig
from sqlalchemy import inspect, text

logger = LoggingConfig.get_logger(__name__)


def check_tables():
    """Check if required tables exist"""
    db = SessionLocal()
    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        required_tables = ['tasks', 'plans', 'ollama_servers', 'ollama_models']
        missing = [t for t in required_tables if t not in tables]
        
        if missing:
            print(f"[!] Missing tables: {missing}")
            print(f"[+] Existing tables: {len(tables)}")
            return False
        else:
            print(f"[OK] All required tables exist")
            print(f"[+] Total tables: {len(tables)}")
            return True
    except Exception as e:
        print(f"[X] Error checking tables: {e}")
        return False
    finally:
        db.close()


def apply_migrations():
    """Apply Alembic migrations"""
    try:
        from alembic import command
        from alembic.config import Config

        # Change to backend directory for alembic.ini
        os.chdir(backend_path)
        
        cfg = Config('alembic.ini')
        print("[+] Applying migrations...")
        command.upgrade(cfg, 'head')
        print("[OK] Migrations applied successfully")
        return True
    except Exception as e:
        print(f"[X] Error applying migrations: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_ollama_servers():
    """Check if Ollama servers are configured"""
    db = SessionLocal()
    try:
        from app.models.ollama import OllamaServer
        
        servers = db.query(OllamaServer).filter(OllamaServer.is_active == True).all()
        
        if not servers:
            print("[!] No active Ollama servers found in database")
            print("[+] You may need to run init_ollama_servers.py")
            return False
        else:
            print(f"[OK] Found {len(servers)} active Ollama server(s)")
            for server in servers:
                print(f"    - {server.name}: {server.url}")
            return True
    except Exception as e:
        print(f"[X] Error checking servers: {e}")
        return False
    finally:
        db.close()


def main():
    """Main setup and test function"""
    print("="*80)
    print("PHASE 6: DATABASE SETUP AND REAL TESTS")
    print("="*80)
    
    # Step 1: Check tables
    print("\n[1] Checking database tables...")
    if not check_tables():
        print("\n[2] Applying migrations...")
        if not apply_migrations():
            print("\n[X] Failed to apply migrations. Please check database connection.")
            return False
        # Check again
        if not check_tables():
            print("\n[X] Tables still missing after migrations. Please check manually.")
            return False
    
    # Step 3: Check Ollama servers
    print("\n[3] Checking Ollama servers...")
    check_ollama_servers()  # Warning only, not critical
    
    # Step 4: Run tests
    print("\n[4] Running Phase 6 real tests...")
    print("="*80)
    
    # Import and run test script
    try:
        import asyncio

        from scripts.test_phase6_complete_real import main as test_main
        
        success = asyncio.run(test_main())
        
        if success:
            print("\n" + "="*80)
            print("[OK] All tests passed!")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("[!] Some tests failed. Check output above.")
            print("="*80)
        
        return success
    except Exception as e:
        print(f"\n[X] Error running tests: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

