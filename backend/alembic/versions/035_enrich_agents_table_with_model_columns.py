"""enrich agents table to match Agent model columns

Revision ID: 035
Revises: 034
Create Date: 2025-12-11 18:30:00.000000
"""
import sqlalchemy as sa
from alembic import op

revision = "035"
down_revision = "034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE IF EXISTS agents
        ADD COLUMN IF NOT EXISTS description text,
        ADD COLUMN IF NOT EXISTS version integer DEFAULT 1,
        ADD COLUMN IF NOT EXISTS parent_agent_id uuid,
        ADD COLUMN IF NOT EXISTS created_by varchar(255),
        ADD COLUMN IF NOT EXISTS updated_at timestamptz,
        ADD COLUMN IF NOT EXISTS activated_at timestamptz,
        ADD COLUMN IF NOT EXISTS last_used_at timestamptz,
        ADD COLUMN IF NOT EXISTS endpoint varchar(255),
        ADD COLUMN IF NOT EXISTS last_heartbeat timestamptz,
        ADD COLUMN IF NOT EXISTS health_status varchar(50) DEFAULT 'unknown',
        ADD COLUMN IF NOT EXISTS last_health_check timestamptz,
        ADD COLUMN IF NOT EXISTS response_time_ms integer,
        ADD COLUMN IF NOT EXISTS system_prompt text,
        ADD COLUMN IF NOT EXISTS model_preference varchar(255),
        ADD COLUMN IF NOT EXISTS temperature varchar(10),
        ADD COLUMN IF NOT EXISTS identity_id varchar(255),
        ADD COLUMN IF NOT EXISTS security_policies jsonb,
        ADD COLUMN IF NOT EXISTS allowed_actions jsonb,
        ADD COLUMN IF NOT EXISTS forbidden_actions jsonb,
        ADD COLUMN IF NOT EXISTS max_concurrent_tasks integer DEFAULT 1,
        ADD COLUMN IF NOT EXISTS rate_limit_per_minute integer,
        ADD COLUMN IF NOT EXISTS memory_limit_mb integer,
        ADD COLUMN IF NOT EXISTS total_tasks_executed integer DEFAULT 0,
        ADD COLUMN IF NOT EXISTS successful_tasks integer DEFAULT 0,
        ADD COLUMN IF NOT EXISTS failed_tasks integer DEFAULT 0,
        ADD COLUMN IF NOT EXISTS average_execution_time integer,
        ADD COLUMN IF NOT EXISTS success_rate varchar(10),
        ADD COLUMN IF NOT EXISTS agent_metadata jsonb,
        ADD COLUMN IF NOT EXISTS tags jsonb;
        """
    )


def downgrade() -> None:
    pass


