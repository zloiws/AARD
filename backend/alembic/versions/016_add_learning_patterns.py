"""Add learning_patterns table

Revision ID: 016_add_learning_patterns
Revises: 015_add_authentication
Create Date: 2025-12-03 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016_add_learning_patterns'
down_revision = '015_add_authentication'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create learning_patterns table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.learning_patterns')")).scalar():
        op.create_table('learning_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('pattern_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('pattern_data', postgresql.JSONB(), nullable=False),
        sa.Column('success_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_executions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_executions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='SET NULL'), nullable=True),
        sa.Column('task_category', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_learning_patterns_type', 'learning_patterns', ['pattern_type'])
    op.create_index('idx_learning_patterns_agent_id', 'learning_patterns', ['agent_id'])
    op.create_index('idx_learning_patterns_success_rate', 'learning_patterns', ['success_rate'])
    op.create_index('idx_learning_patterns_task_category', 'learning_patterns', ['task_category'])


def downgrade() -> None:
    op.drop_index('idx_learning_patterns_task_category', table_name='learning_patterns')
    op.drop_index('idx_learning_patterns_success_rate', table_name='learning_patterns')
    op.drop_index('idx_learning_patterns_agent_id', table_name='learning_patterns')
    op.drop_index('idx_learning_patterns_type', table_name='learning_patterns')
    op.drop_table('learning_patterns')

