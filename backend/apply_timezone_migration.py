#!/usr/bin/env python3
"""Apply timezone datetime migration"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.database import engine
from sqlalchemy import text

def apply_migration():
    """Apply the timezone migration"""
    migration_file = Path(__file__).parent / "migrate_timezone_datetime.sql"

    if not migration_file.exists():
        print(f"Migration file not found: {migration_file}")
        return False

    print("Applying timezone datetime migration...")

    try:
        with engine.connect() as conn:
            with open(migration_file, 'r') as f:
                sql = f.read()

            # Execute the migration
            conn.execute(text(sql))
            conn.commit()

            print("✅ Timezone migration applied successfully!")
            return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
