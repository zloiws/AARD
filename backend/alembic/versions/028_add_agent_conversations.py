"""Add agent conversations table

Revision ID: 028_add_agent_conversations
Revises: 027_add_agent_teams
Create Date: 2024-12-05 23:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '028_add_agent_conversations'
down_revision = '027_add_agent_teams'
branch_labels = None
depends_on = None


def upgrade():
    # Create agent_conversations table
    op.create_table(
        'agent_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('participants', postgresql.JSONB(), nullable=False),
        sa.Column('messages', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('context', postgresql.JSONB(), nullable=True),
        sa.Column('goal', sa.Text(), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='initiated'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('task_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('tasks.id'), nullable=True),
        sa.Column('conversation_metadata', postgresql.JSONB(), nullable=True),
    )
    
    # Create index on task_id for faster lookups
    op.create_index('ix_agent_conversations_task_id', 'agent_conversations', ['task_id'])
    
    # Create index on status for filtering
    op.create_index('ix_agent_conversations_status', 'agent_conversations', ['status'])
    
    # Create index on created_at for sorting
    op.create_index('ix_agent_conversations_created_at', 'agent_conversations', ['created_at'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_agent_conversations_created_at', table_name='agent_conversations')
    op.drop_index('ix_agent_conversations_status', table_name='agent_conversations')
    op.drop_index('ix_agent_conversations_task_id', table_name='agent_conversations')
    
    # Drop table
    op.drop_table('agent_conversations')

