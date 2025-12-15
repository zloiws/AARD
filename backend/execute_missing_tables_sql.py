#!/usr/bin/env python3
"""Execute SQL script to create missing tables"""
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

def execute_sql_file():
    """Execute the SQL file to create missing tables"""
    from app.core.database import engine

    sql_file = Path(__file__).parent / "create_missing_tables.sql"

    if not sql_file.exists():
        print(f"SQL file not found: {sql_file}")
        return False

    print(f"Executing SQL file: {sql_file}")

    try:
        with engine.connect() as conn:
            with open(sql_file, 'r') as f:
                sql_content = f.read()

            # Execute the SQL
            conn.execute(text(sql_content))
            conn.commit()

            print("SQL executed successfully!")

            # Verify tables were created
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('checkpoints', 'approval_requests', 'evolution_history', 'feedback')"))
            created_tables = [row[0] for row in result.fetchall()]

            print(f"Created tables: {created_tables}")
            expected_tables = {'checkpoints', 'approval_requests', 'evolution_history', 'feedback'}

            if expected_tables.issubset(set(created_tables)):
                print("All missing tables created successfully!")
                return True
            else:
                missing = expected_tables - set(created_tables)
                print(f"Some tables still missing: {missing}")
                return False

    except Exception as e:
        print(f"Error executing SQL: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = execute_sql_file()
    sys.exit(0 if success else 1)
