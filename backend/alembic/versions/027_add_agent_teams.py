"""Add agent teams

Revision ID: 027_add_agent_teams
Revises: 026_add_plan_templates
Create Date: 2025-12-05 21:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '027_add_agent_teams'
down_revision = '026_add_plan_templates'
branch_labels = None
depends_on = None


def upgrade():
    # Create agent_teams table if not exists (idempotent)
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agent_teams') THEN
            CREATE TABLE agent_teams (
                id UUID PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                description TEXT,
                roles JSONB,
                coordination_strategy VARCHAR(50) NOT NULL DEFAULT 'collaborative',
                status VARCHAR(50) NOT NULL DEFAULT 'draft',
                created_by VARCHAR(255),
                created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                team_metadata JSONB
            );
        END IF;
    END
    $$;
    """)

    # Create agent_team_associations table if not exists
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'agent_team_associations') THEN
            CREATE TABLE agent_team_associations (
                team_id UUID NOT NULL REFERENCES agent_teams(id) ON DELETE CASCADE,
                agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
                role VARCHAR(100),
                assigned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
                is_lead BOOLEAN NOT NULL DEFAULT false,
                PRIMARY KEY (team_id, agent_id)
            );
        END IF;
    END
    $$;
    """)

    # Create indexes if not exists
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_teams_name ON agent_teams (name);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_teams_status ON agent_teams (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_team_associations_team_id ON agent_team_associations (team_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_team_associations_agent_id ON agent_team_associations (agent_id);")


def downgrade():
    # Drop indexes
    op.drop_index('ix_agent_team_associations_agent_id', table_name='agent_team_associations')
    op.drop_index('ix_agent_team_associations_team_id', table_name='agent_team_associations')
    op.drop_index('ix_agent_teams_status', table_name='agent_teams')
    op.drop_index('ix_agent_teams_name', table_name='agent_teams')
    
    # Drop tables
    op.drop_table('agent_team_associations')
    op.drop_table('agent_teams')

