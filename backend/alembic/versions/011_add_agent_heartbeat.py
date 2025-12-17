"""Add heartbeat and health fields to agents

Revision ID: 011_add_agent_heartbeat
Revises: 010_add_tools
Create Date: 2025-12-03 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_add_agent_heartbeat'
down_revision = '010_add_tools'
branch_labels = None
depends_on = None


def upgrade():
    # Add heartbeat and health fields to agents table (idempotent)
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS endpoint VARCHAR(255);")
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMP;")
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS health_status VARCHAR(50) DEFAULT 'unknown';")
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS last_health_check TIMESTAMP;")
    op.execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS response_time_ms INTEGER;")

    # Create index for health status (idempotent)
    op.execute("CREATE INDEX IF NOT EXISTS ix_agents_health_status ON agents (health_status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agents_last_heartbeat ON agents (last_heartbeat);")


def downgrade():
    # Drop indexes and columns if they exist (idempotent)
    op.execute("DROP INDEX IF EXISTS ix_agents_last_heartbeat;")
    op.execute("DROP INDEX IF EXISTS ix_agents_health_status;")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS response_time_ms;")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS last_health_check;")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS health_status;")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS last_heartbeat;")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS endpoint;")

