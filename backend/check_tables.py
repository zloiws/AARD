#!/usr/bin/env python3
"""Check existing tables"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text

def check_tables():
    """Check which tables exist"""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
        tables = [row[0] for row in result.fetchall()]
        print('All tables:', tables)
        target_tables = ['tasks', 'approval_requests', 'users']
        existing = [t for t in target_tables if t in tables]
        print('Tables to migrate:', existing)
        return existing

if __name__ == "__main__":
    check_tables()
