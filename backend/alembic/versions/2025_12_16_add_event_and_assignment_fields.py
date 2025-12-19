"""add event and prompt_assignment fields

Revision ID: 20251216_event_assignment_enrich
Revises: 20251215_interpretation_timeline
Create Date: 2025-12-16 00:00:00.000000
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251216_event_assignment_enrich"
down_revision = "20251215_interpretation_timeline"
branch_labels = None
depends_on = None


def upgrade():
    # Add columns to workflow_events (idempotent)
    op.execute("ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS component_role VARCHAR(100);")
    op.execute("ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS prompt_id UUID;")
    op.execute("ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS prompt_version VARCHAR(50);")
    op.execute("ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS decision_source VARCHAR(50);")
    # Create indexes for new fields (idempotent)
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_events_component_role ON workflow_events (component_role);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_events_prompt_id ON workflow_events (prompt_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_events_decision_source ON workflow_events (decision_source);")

    # Add columns to prompt_assignments (idempotent)
    # Add columns to prompt_assignments (idempotent) only if table exists
    conn = op.get_bind()
    if conn.execute(sa.text("select to_regclass('public.prompt_assignments')")).scalar():
        op.execute("ALTER TABLE prompt_assignments ADD COLUMN IF NOT EXISTS component_role VARCHAR(100) DEFAULT 'unknown';")
        op.execute("ALTER TABLE prompt_assignments ADD COLUMN IF NOT EXISTS stage VARCHAR(100) DEFAULT 'unknown';")
        op.execute("ALTER TABLE prompt_assignments ADD COLUMN IF NOT EXISTS scope VARCHAR(50) DEFAULT 'global';")
        op.execute("ALTER TABLE prompt_assignments ADD COLUMN IF NOT EXISTS agent_id UUID;")
        op.execute("ALTER TABLE prompt_assignments ADD COLUMN IF NOT EXISTS experiment_id UUID;")
        # Create indexes (idempotent)
        op.execute("CREATE INDEX IF NOT EXISTS ix_prompt_assignments_component_role ON prompt_assignments (component_role);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_prompt_assignments_stage ON prompt_assignments (stage);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_prompt_assignments_scope ON prompt_assignments (scope);")


def downgrade():
    # Drop indexes and columns from prompt_assignments (idempotent)
    op.execute("DROP INDEX IF EXISTS ix_prompt_assignments_scope;")
    op.execute("DROP INDEX IF EXISTS ix_prompt_assignments_stage;")
    op.execute("DROP INDEX IF EXISTS ix_prompt_assignments_component_role;")
    op.execute("ALTER TABLE prompt_assignments DROP COLUMN IF EXISTS experiment_id;")
    op.execute("ALTER TABLE prompt_assignments DROP COLUMN IF EXISTS agent_id;")
    op.execute("ALTER TABLE prompt_assignments DROP COLUMN IF EXISTS scope;")
    op.execute("ALTER TABLE prompt_assignments DROP COLUMN IF EXISTS stage;")
    op.execute("ALTER TABLE prompt_assignments DROP COLUMN IF EXISTS component_role;")

    # Drop indexes and columns from workflow_events (idempotent)
    op.execute("DROP INDEX IF EXISTS ix_workflow_events_decision_source;")
    op.execute("DROP INDEX IF EXISTS ix_workflow_events_prompt_id;")
    op.execute("DROP INDEX IF EXISTS ix_workflow_events_component_role;")
    op.execute("ALTER TABLE workflow_events DROP COLUMN IF EXISTS decision_source;")
    op.execute("ALTER TABLE workflow_events DROP COLUMN IF EXISTS prompt_version;")
    op.execute("ALTER TABLE workflow_events DROP COLUMN IF EXISTS prompt_id;")
    op.execute("ALTER TABLE workflow_events DROP COLUMN IF EXISTS component_role;")

