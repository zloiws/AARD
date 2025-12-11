"""add workflow events table

Revision ID: 020_add_workflow_events
Revises: 019_add_chat_sessions
Create Date: 2025-01-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '020_add_workflow_events'
down_revision = '019_add_chat_sessions'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create workflow_events table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.workflow_events')")).scalar():
        op.create_table('workflow_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('workflow_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_source', sa.String(length=50), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='in_progress'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('event_data', postgresql.JSONB(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approval_request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('trace_id', sa.String(length=255), nullable=True),
        sa.Column('parent_event_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tool_id'], ['artifacts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approval_request_id'], ['approval_requests.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_event_id'], ['workflow_events.id'], ondelete='SET NULL'),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed', 'cancelled', 'pending')",
            name='workflow_events_status_check'
        ),
    )
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_workflow_id ON workflow_events (workflow_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_timestamp ON workflow_events (timestamp);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_type_source ON workflow_events (event_type, event_source);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_stage_status ON workflow_events (stage, status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_task_id ON workflow_events (task_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_trace_id ON workflow_events (trace_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_workflow_events_session_id ON workflow_events (session_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_events_event_type ON workflow_events (event_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_events_event_source ON workflow_events (event_source);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_events_stage ON workflow_events (stage);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_workflow_events_status ON workflow_events (status);")


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_workflow_events_status', table_name='workflow_events')
    op.drop_index('ix_workflow_events_stage', table_name='workflow_events')
    op.drop_index('ix_workflow_events_event_source', table_name='workflow_events')
    op.drop_index('ix_workflow_events_event_type', table_name='workflow_events')
    op.drop_index('idx_workflow_events_session_id', table_name='workflow_events')
    op.drop_index('idx_workflow_events_trace_id', table_name='workflow_events')
    op.drop_index('idx_workflow_events_task_id', table_name='workflow_events')
    op.drop_index('idx_workflow_events_stage_status', table_name='workflow_events')
    op.drop_index('idx_workflow_events_type_source', table_name='workflow_events')
    op.drop_index('idx_workflow_events_timestamp', table_name='workflow_events')
    op.drop_index('idx_workflow_events_workflow_id', table_name='workflow_events')
    
    # Drop table
    op.drop_table('workflow_events')

