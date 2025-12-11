"""Add execution_traces table

Revision ID: 005_add_execution_traces
Revises: 004_add_plan_id_to_approval_requests
Create Date: 2025-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_execution_traces'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Create execution_traces table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.execution_traces')")).scalar():
        op.create_table('execution_traces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('trace_id', sa.String(255), nullable=False, unique=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('span_id', sa.String(255), nullable=True),
        sa.Column('parent_span_id', sa.String(255), nullable=True),
        sa.Column('operation_name', sa.String(255), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('attributes', postgresql.JSONB, nullable=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tool_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('error_message', sa.String(1000), nullable=True),
        sa.Column('error_type', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("status IN ('success', 'error', 'timeout')", name='execution_traces_status_check'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL', name='fk_execution_traces_task_id'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='SET NULL', name='fk_execution_traces_plan_id'),
    )
    
    # Create indexes
    op.create_index('idx_traces_trace_id', 'execution_traces', ['trace_id'])
    op.create_index('idx_traces_task_id', 'execution_traces', ['task_id'])
    op.create_index('idx_traces_plan_id', 'execution_traces', ['plan_id'])
    op.create_index('idx_traces_agent_id', 'execution_traces', ['agent_id'])
    op.create_index('idx_traces_start_time', 'execution_traces', ['start_time'])
    op.create_index('idx_traces_status', 'execution_traces', ['status'])
    op.create_index('idx_traces_operation', 'execution_traces', ['operation_name'])
    op.create_index('idx_traces_span_id', 'execution_traces', ['span_id'])
    op.create_index('idx_traces_parent_span_id', 'execution_traces', ['parent_span_id'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_traces_parent_span_id', table_name='execution_traces')
    op.drop_index('idx_traces_span_id', table_name='execution_traces')
    op.drop_index('idx_traces_operation', table_name='execution_traces')
    op.drop_index('idx_traces_status', table_name='execution_traces')
    op.drop_index('idx_traces_start_time', table_name='execution_traces')
    op.drop_index('idx_traces_agent_id', table_name='execution_traces')
    op.drop_index('idx_traces_plan_id', table_name='execution_traces')
    op.drop_index('idx_traces_task_id', table_name='execution_traces')
    op.drop_index('idx_traces_trace_id', table_name='execution_traces')
    
    # Drop table
    op.drop_table('execution_traces')

