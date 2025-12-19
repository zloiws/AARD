"""
Apply migration 020_add_workflow_events manually
"""
import sys
from pathlib import Path

# Add backend to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings
from sqlalchemy import create_engine, text


def apply_migration():
    """Apply migration 020_add_workflow_events"""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    
    with engine.begin() as conn:
        # Check if table already exists
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'workflow_events'
        """))
        existing_tables = {row[0] for row in result}
        
        if 'workflow_events' in existing_tables:
            print("✅ Table workflow_events already exists. Skipping migration.")
            return
        
        print("Creating workflow_events table...")
        conn.execute(text("""
            CREATE TABLE workflow_events (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                workflow_id VARCHAR(255) NOT NULL,
                event_type VARCHAR(50) NOT NULL,
                event_source VARCHAR(50) NOT NULL,
                stage VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'in_progress',
                message TEXT NOT NULL,
                event_data JSONB,
                metadata JSONB,
                task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
                plan_id UUID REFERENCES plans(id) ON DELETE SET NULL,
                tool_id UUID REFERENCES artifacts(id) ON DELETE SET NULL,
                approval_request_id UUID REFERENCES approval_requests(id) ON DELETE SET NULL,
                session_id VARCHAR(255),
                trace_id VARCHAR(255),
                parent_event_id UUID REFERENCES workflow_events(id) ON DELETE SET NULL,
                timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                duration_ms INTEGER,
                CHECK (status IN ('in_progress', 'completed', 'failed', 'cancelled', 'pending'))
            )
        """))
        
        print("Creating indexes...")
        conn.execute(text("CREATE INDEX idx_workflow_events_workflow_id ON workflow_events(workflow_id)"))
        conn.execute(text("CREATE INDEX idx_workflow_events_timestamp ON workflow_events(timestamp)"))
        conn.execute(text("CREATE INDEX idx_workflow_events_type_source ON workflow_events(event_type, event_source)"))
        conn.execute(text("CREATE INDEX idx_workflow_events_stage_status ON workflow_events(stage, status)"))
        conn.execute(text("CREATE INDEX idx_workflow_events_task_id ON workflow_events(task_id)"))
        conn.execute(text("CREATE INDEX idx_workflow_events_trace_id ON workflow_events(trace_id)"))
        conn.execute(text("CREATE INDEX idx_workflow_events_session_id ON workflow_events(session_id)"))
        conn.execute(text("CREATE INDEX ix_workflow_events_event_type ON workflow_events(event_type)"))
        conn.execute(text("CREATE INDEX ix_workflow_events_event_source ON workflow_events(event_source)"))
        conn.execute(text("CREATE INDEX ix_workflow_events_stage ON workflow_events(stage)"))
        conn.execute(text("CREATE INDEX ix_workflow_events_status ON workflow_events(status)"))
        
        # Update alembic_version
        conn.execute(text("""
            INSERT INTO alembic_version (version_num)
            VALUES ('020_add_workflow_events')
            ON CONFLICT (version_num) DO NOTHING
        """))
        
        print("✅ Migration 020_add_workflow_events applied successfully!")

if __name__ == "__main__":
    apply_migration()

