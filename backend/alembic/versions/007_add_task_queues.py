"""Add task_queues and queue_tasks tables

Revision ID: 007_add_task_queues
Revises: 006_add_request_logs
Create Date: 2025-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007_add_task_queues'
down_revision = '006_add_request_logs'
branch_labels = None
depends_on = None


def upgrade():
    # Create task_queues table
    op.create_table(
        'task_queues',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('max_concurrent', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
    )
    
    # Create indexes for task_queues
    op.create_index('idx_task_queues_name', 'task_queues', ['name'])
    op.create_index('idx_task_queues_active', 'task_queues', ['is_active'])
    op.create_index('idx_task_queues_priority', 'task_queues', ['priority'])
    
    # Create queue_tasks table
    op.create_table(
        'queue_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('queue_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('task_data', postgresql.JSONB, nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('next_retry_at', sa.DateTime(), nullable=True),
        sa.Column('result_data', postgresql.JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('assigned_worker', sa.String(255), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("status IN ('pending', 'queued', 'processing', 'completed', 'failed', 'cancelled')", name='queue_tasks_status_check'),
        sa.ForeignKeyConstraint(['queue_id'], ['task_queues.id'], ondelete='CASCADE', name='fk_queue_tasks_queue_id'),
    )
    
    # Create indexes for queue_tasks
    op.create_index('idx_queue_tasks_status', 'queue_tasks', ['status'])
    op.create_index('idx_queue_tasks_priority', 'queue_tasks', ['priority'])
    op.create_index('idx_queue_tasks_next_retry', 'queue_tasks', ['next_retry_at'])
    op.create_index('idx_queue_tasks_queue', 'queue_tasks', ['queue_id'])
    op.create_index('idx_queue_tasks_type', 'queue_tasks', ['task_type'])
    op.create_index('idx_queue_tasks_worker', 'queue_tasks', ['assigned_worker'])
    op.create_index('idx_queue_tasks_created', 'queue_tasks', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_queue_tasks_created', table_name='queue_tasks')
    op.drop_index('idx_queue_tasks_worker', table_name='queue_tasks')
    op.drop_index('idx_queue_tasks_type', table_name='queue_tasks')
    op.drop_index('idx_queue_tasks_queue', table_name='queue_tasks')
    op.drop_index('idx_queue_tasks_next_retry', table_name='queue_tasks')
    op.drop_index('idx_queue_tasks_priority', table_name='queue_tasks')
    op.drop_index('idx_queue_tasks_status', table_name='queue_tasks')
    op.drop_index('idx_task_queues_priority', table_name='task_queues')
    op.drop_index('idx_task_queues_active', table_name='task_queues')
    op.drop_index('idx_task_queues_name', table_name='task_queues')
    
    # Drop tables
    op.drop_table('queue_tasks')
    op.drop_table('task_queues')

