#!/usr/bin/env python3
"""Check for missing tables that were causing test failures"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text

# Set database URL
os.environ['DATABASE_URL'] = 'postgresql://postgres:Cdthrf12@10.39.0.101:5432/aard'

engine = create_engine(os.environ['DATABASE_URL'])

missing_tables = ['checkpoints', 'approval_requests', 'evolution_history', 'feedback', 'request_logs']

try:
    with engine.connect() as conn:
        # Check what tables exist
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"))
        existing_tables = {row[0] for row in result.fetchall()}

        actually_missing = [table for table in missing_tables if table not in existing_tables]

        print(f"Checking for tables: {missing_tables}")
        print(f"Existing tables: {sorted(existing_tables)}")
        print(f"Actually missing: {actually_missing}")

        if not actually_missing:
            print("✅ All required tables exist!")
        else:
            print("❌ Missing tables:", actually_missing)

except Exception as e:
    print(f"Database connection error: {e}")
    sys.exit(1)