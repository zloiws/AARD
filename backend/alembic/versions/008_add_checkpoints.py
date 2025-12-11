"""Add checkpoints table

Revision ID: 008_add_checkpoints
Revises: 007_add_task_queues
Create Date: 2025-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008_add_checkpoints'
down_revision = '007_add_task_queues'
branch_labels = None
depends_on = None


def upgrade():
    # Create checkpoints table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.checkpoints')")).scalar():
        op.create_table('checkpoints',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('state_data', postgresql.JSONB, nullable=False),
        sa.Column('state_hash', sa.String(64), nullable=True),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('trace_id', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(['request_id'], ['request_logs.id'], ondelete='SET NULL', name='fk_checkpoints_request_id'),
    )
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_entity ON checkpoints (entity_type, entity_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints (created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_hash ON checkpoints (state_hash);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_trace ON checkpoints (trace_id);")


def downgrade():
    # Drop indexes
    op.drop_index('idx_checkpoints_trace', table_name='checkpoints')
    op.drop_index('idx_checkpoints_hash', table_name='checkpoints')
    op.drop_index('idx_checkpoints_created', table_name='checkpoints')
    op.drop_index('idx_checkpoints_entity', table_name='checkpoints')
    
    # Drop table
    op.drop_table('checkpoints')

