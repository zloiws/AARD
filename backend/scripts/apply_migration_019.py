"""
Apply migration 019_add_chat_sessions manually
"""
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from sqlalchemy import create_engine, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID


def apply_migration():
    """Apply migration 019_add_chat_sessions"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.begin() as conn:
        # Check if tables already exist
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('chat_sessions', 'chat_messages')
        """))
        existing_tables = {row[0] for row in result}
        
        if 'chat_sessions' in existing_tables and 'chat_messages' in existing_tables:
            print("✅ Tables chat_sessions and chat_messages already exist. Skipping migration.")
            return
        
        print("Creating chat_sessions table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                system_prompt TEXT,
                title VARCHAR(255),
                user_id UUID,
                metadata JSONB DEFAULT '{}'::jsonb
            )
        """))
        
        print("Creating chat_messages table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
                role VARCHAR(50) NOT NULL,
                content TEXT NOT NULL,
                model VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                metadata JSONB DEFAULT '{}'::jsonb,
                sequence INTEGER NOT NULL DEFAULT 0
            )
        """))
        
        print("Creating indexes...")
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages(session_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_chat_messages_created_at ON chat_messages(created_at)"))
        
        # Update alembic_version
        conn.execute(text("""
            INSERT INTO alembic_version (version_num)
            VALUES ('019_add_chat_sessions')
            ON CONFLICT (version_num) DO NOTHING
        """))
        
        print("✅ Migration 019_add_chat_sessions applied successfully!")

if __name__ == "__main__":
    apply_migration()

