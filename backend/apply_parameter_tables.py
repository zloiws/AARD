"""
Apply SQL script to create parameter tables directly
"""
import sys
from pathlib import Path

from app.core.database import engine
from sqlalchemy import text

BACKEND_DIR = Path(__file__).resolve().parent
SQL_FILE = BACKEND_DIR / "create_parameter_tables.sql"

try:
    print("Reading SQL script...")
    sql_content = SQL_FILE.read_text(encoding="utf-8")
    
    print("Executing SQL script...")
    with engine.begin() as conn:  # Use begin() for transaction
        # Execute the entire script as one transaction
        try:
            conn.execute(text(sql_content))
            print("  ✅ All statements executed successfully")
        except Exception as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                print(f"  ⚠️  Some objects already exist (this is OK): {str(e)[:200]}")
            else:
                print(f"  ❌ Error: {e}")
                raise
    
    print("\n✅ Parameter tables created successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

