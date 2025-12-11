"""Add agent conversations table

Revision ID: 028_add_agent_conversations
Revises: 027_add_agent_teams
Create Date: 2024-12-05 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '028_add_agent_conversations'
down_revision = '027_add_agent_teams'
branch_labels = None
depends_on = None


def upgrade():
    # Create agent_conversations table if not exists
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agent_conversations') THEN
            CREATE TABLE agent_conversations (
                id UUID PRIMARY KEY,
                title VARCHAR(255),
                description TEXT,
                participants JSONB NOT NULL,
                messages JSONB NOT NULL DEFAULT '[]'::jsonb,
                context JSONB,
                goal TEXT,
                status VARCHAR(50) NOT NULL DEFAULT 'initiated',
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                completed_at TIMESTAMP WITHOUT TIME ZONE,
                task_id UUID REFERENCES tasks(id),
                conversation_metadata JSONB
            );
        END IF;
    END
    $$;
    """)

    # Create indexes if not exists
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_conversations_task_id ON agent_conversations (task_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_conversations_status ON agent_conversations (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_conversations_created_at ON agent_conversations (created_at);")


def downgrade():
    # Drop indexes
    op.drop_index('ix_agent_conversations_created_at', table_name='agent_conversations')
    op.drop_index('ix_agent_conversations_status', table_name='agent_conversations')
    op.drop_index('ix_agent_conversations_task_id', table_name='agent_conversations')
    
    # Drop table
    op.drop_table('agent_conversations')

