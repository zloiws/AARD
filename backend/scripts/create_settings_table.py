"""
Создание таблицы system_settings напрямую через SQL
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.database import engine
from sqlalchemy import text

def create_table():
    """Создать таблицу system_settings"""
    print("Creating system_settings table...")
    
    sql = """
    CREATE TABLE IF NOT EXISTS system_settings (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        key VARCHAR(255) UNIQUE NOT NULL,
        value TEXT,
        value_type VARCHAR(20) NOT NULL DEFAULT 'string',
        category VARCHAR(50) NOT NULL,
        module VARCHAR(100),
        description TEXT,
        is_active BOOLEAN NOT NULL DEFAULT true,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_by VARCHAR(255)
    );
    
    CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings(key);
    CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings(category);
    CREATE INDEX IF NOT EXISTS idx_system_settings_module ON system_settings(module);
    CREATE INDEX IF NOT EXISTS idx_settings_category_active ON system_settings(category, is_active);
    """
    
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        print("Table created successfully!")
        return True
    except Exception as e:
        print(f"Error creating table: {e}")
        return False

if __name__ == "__main__":
    if create_table():
        print("\nTable system_settings is ready.")
        print("Run: python scripts/migrate_env_to_db.py")
    else:
        sys.exit(1)

