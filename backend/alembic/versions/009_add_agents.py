"""Add agents table

Revision ID: 009_add_agents
Revises: 008_add_checkpoints
Create Date: 2025-12-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '009_add_agents'
down_revision = '008_add_checkpoints'
branch_labels = None
depends_on = None


def upgrade():
    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Identity and versioning
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('parent_agent_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Status and lifecycle
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        
        # Agent configuration
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('capabilities', postgresql.JSONB(), nullable=True),
        sa.Column('model_preference', sa.String(255), nullable=True),
        sa.Column('temperature', sa.String(10), nullable=True, server_default='0.7'),
        
        # Security and permissions
        sa.Column('identity_id', sa.String(255), nullable=True),
        sa.Column('security_policies', postgresql.JSONB(), nullable=True),
        sa.Column('allowed_actions', postgresql.JSONB(), nullable=True),
        sa.Column('forbidden_actions', postgresql.JSONB(), nullable=True),
        
        # Resource limits
        sa.Column('max_concurrent_tasks', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True),
        sa.Column('memory_limit_mb', sa.Integer(), nullable=True),
        
        # Metrics and performance
        sa.Column('total_tasks_executed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_tasks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_execution_time', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.String(10), nullable=True),
        
        # Metadata (renamed to agent_metadata to avoid SQLAlchemy reserved name)
        sa.Column('agent_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
    )
    
    # Add foreign key
    op.create_foreign_key(
        'fk_agents_parent_agent_id',
        'agents', 'agents',
        ['parent_agent_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes
    op.create_index('ix_agents_name', 'agents', ['name'], unique=True)
    op.create_index('ix_agents_status', 'agents', ['status'])
    op.create_index('ix_agents_created_at', 'agents', ['created_at'])
    op.create_index('ix_agents_capabilities', 'agents', ['capabilities'], postgresql_using='gin')
    op.create_index('ix_agents_tags', 'agents', ['tags'], postgresql_using='gin')


def downgrade():
    op.drop_index('ix_agents_tags', table_name='agents')
    op.drop_index('ix_agents_capabilities', table_name='agents')
    op.drop_index('ix_agents_created_at', table_name='agents')
    op.drop_index('ix_agents_status', table_name='agents')
    op.drop_index('ix_agents_name', table_name='agents')
    op.drop_table('agents')

