"""Add request_logs and request_consequences tables

Revision ID: 006_add_request_logs
Revises: 005_add_execution_traces
Create Date: 2025-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_request_logs'
down_revision = '005_add_execution_traces'
branch_labels = None
depends_on = None


def upgrade():
    # Create request_logs table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.request_logs')")).scalar():
        op.create_table('request_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('request_type', sa.String(50), nullable=False),
        sa.Column('request_data', postgresql.JSONB, nullable=False),
        sa.Column('model_used', sa.String(255), nullable=True),
        sa.Column('server_url', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('response_data', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_artifacts', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('created_plans', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('created_approvals', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('modified_artifacts', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column('success_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('importance_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('impact_score', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('overall_rank', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('trace_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("status IN ('success', 'failed', 'timeout', 'cancelled')", name='request_logs_status_check'),
    )
    
    # Create indexes for request_logs
    op.create_index('idx_request_logs_status', 'request_logs', ['status'])
    op.create_index('idx_request_logs_type', 'request_logs', ['request_type'])
    op.create_index('idx_request_logs_rank', 'request_logs', ['overall_rank'])
    op.create_index('idx_request_logs_created_at', 'request_logs', ['created_at'])
    op.create_index('idx_request_logs_model', 'request_logs', ['model_used'])
    op.create_index('idx_request_logs_trace_id', 'request_logs', ['trace_id'])
    op.create_index('idx_request_logs_session_id', 'request_logs', ['session_id'])
    
    # Create request_consequences table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.request_consequences')")).scalar():
        op.create_table('request_consequences',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('consequence_type', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('impact_type', sa.String(50), nullable=True),
        sa.Column('impact_description', sa.Text(), nullable=True),
        sa.Column('impact_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['request_id'], ['request_logs.id'], ondelete='CASCADE', name='fk_request_consequences_request_id'),
    )
    
    # Create indexes for request_consequences
    op.create_index('idx_consequences_request', 'request_consequences', ['request_id'])
    op.create_index('idx_consequences_entity', 'request_consequences', ['entity_type', 'entity_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_consequences_entity', table_name='request_consequences')
    op.drop_index('idx_consequences_request', table_name='request_consequences')
    op.drop_index('idx_request_logs_session_id', table_name='request_logs')
    op.drop_index('idx_request_logs_trace_id', table_name='request_logs')
    op.drop_index('idx_request_logs_model', table_name='request_logs')
    op.drop_index('idx_request_logs_created_at', table_name='request_logs')
    op.drop_index('idx_request_logs_rank', table_name='request_logs')
    op.drop_index('idx_request_logs_type', table_name='request_logs')
    op.drop_index('idx_request_logs_status', table_name='request_logs')
    
    # Drop tables
    op.drop_table('request_consequences')
    op.drop_table('request_logs')

