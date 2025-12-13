#!/usr/bin/env python3
"""Check current database migration state"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, text

# Set database URL
os.environ['DATABASE_URL'] = 'postgresql://postgres:Cdthrf12@10.39.0.101:5432/aard'

engine = create_engine(os.environ['DATABASE_URL'])

try:
    with engine.connect() as conn:
        # Check alembic version
        try:
            result = conn.execute(text('SELECT version_num FROM alembic_version'))
            version = result.fetchone()
            print(f"Current alembic version: {version[0] if version else 'None'}")
        except Exception as e:
            print(f"No alembic_version table or error: {e}")

        # Check what tables exist
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
        tables = result.fetchall()
        print(f"\nExisting tables ({len(tables)}):")
        for table in tables:
            print(f"  {table[0]}")

except Exception as e:
    print(f"Database connection error: {e}")
    sys.exit(1)
