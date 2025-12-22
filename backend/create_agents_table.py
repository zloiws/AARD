"""Create agents table directly if missing"""
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

from app.core.config import get_settings
from sqlalchemy import create_engine, text

if __name__ == "__main__":
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    # Check if agents table exists
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'agents'
            );
        """))
        exists = result.scalar()
        
        if exists:
            print("✓ Agents table already exists")
        else:
            print("Creating agents table...")
            # Read the migration file to get exact table structure
            migration_file = Path(__file__).parent / "alembic" / "versions" / "009_add_agents.py"
            if migration_file.exists():
                # Execute the migration SQL directly
                conn.execute(text("""
                    CREATE TABLE agents (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR(255) NOT NULL UNIQUE,
                        description TEXT,
                        version INTEGER NOT NULL DEFAULT 1,
                        parent_agent_id UUID,
                        status VARCHAR(50) NOT NULL DEFAULT 'draft',
                        created_by VARCHAR(255),
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        activated_at TIMESTAMP,
                        last_used_at TIMESTAMP,
                        endpoint VARCHAR(500),
                        last_heartbeat TIMESTAMP,
                        health_status VARCHAR(50),
                        last_health_check TIMESTAMP,
                        response_time_ms INTEGER,
                        system_prompt TEXT,
                        capabilities JSONB,
                        model_preference VARCHAR(255),
                        temperature VARCHAR(10) DEFAULT '0.7',
                        identity_id VARCHAR(255),
                        security_policies JSONB,
                        allowed_actions JSONB,
                        forbidden_actions JSONB,
                        max_concurrent_tasks INTEGER,
                        rate_limit_per_minute INTEGER,
                        memory_limit_mb INTEGER,
                        total_tasks_executed INTEGER DEFAULT 0,
                        successful_tasks INTEGER DEFAULT 0,
                        failed_tasks INTEGER DEFAULT 0,
                        average_execution_time INTEGER,
                        success_rate DECIMAL(5,2),
                        agent_metadata JSONB,
                        tags JSONB
                    );
                """))
            conn.commit()
            print("✓ Agents table created successfully!")

