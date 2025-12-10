"""
Apply SQL script to create parameter tables directly
"""
import sys
from pathlib import Path
from sqlalchemy import text
from app.core.database import engine

BACKEND_DIR = Path(__file__).resolve().parent
SQL_FILE = BACKEND_DIR / "create_parameter_tables.sql"

try:
    print("Reading SQL script...")
    sql_content = SQL_FILE.read_text(encoding="utf-8")
    
    print("Executing SQL script...")
    with engine.connect() as conn:
        # Execute each statement separately
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        
        for i, statement in enumerate(statements, 1):
            if statement:
                try:
                    conn.execute(text(statement))
                    print(f"  ✅ Statement {i}/{len(statements)} executed")
                except Exception as e:
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"  ⚠️  Statement {i} skipped (already exists): {str(e)[:100]}")
                    else:
                        print(f"  ❌ Statement {i} failed: {e}")
                        raise
        
        conn.commit()
    
    print("\n✅ Parameter tables created successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

