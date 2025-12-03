"""Add agent memory tables

Revision ID: 014_add_agent_memory
Revises: 013_add_agent_gym
Create Date: 2025-12-03 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '014_add_agent_memory'
down_revision = '013_add_agent_gym'
branch_labels = None
depends_on = None


def upgrade():
    # Create agent_memories table (long-term memory)
    op.create_table(
        'agent_memories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_type', sa.String(50), nullable=False),
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('importance', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed_at', sa.DateTime(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('source', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_agent_memories_agent_id', 'agent_memories', ['agent_id'])
    op.create_index('ix_agent_memories_memory_type', 'agent_memories', ['memory_type'])
    op.create_index('ix_agent_memories_importance', 'agent_memories', ['importance'])
    op.create_index('ix_agent_memories_last_accessed_at', 'agent_memories', ['last_accessed_at'])
    op.create_index('ix_agent_memories_expires_at', 'agent_memories', ['expires_at'])
    # GIN index for JSONB content search
    op.execute('CREATE INDEX ix_agent_memories_content ON agent_memories USING GIN (content)')
    op.execute('CREATE INDEX ix_agent_memories_tags ON agent_memories USING GIN (tags)')
    
    # Create memory_entries table (short-term memory)
    op.create_table(
        'memory_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('context_key', sa.String(255), nullable=False),
        sa.Column('content', postgresql.JSONB(), nullable=False),
        sa.Column('ttl_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_memory_entries_agent_id', 'memory_entries', ['agent_id'])
    op.create_index('ix_memory_entries_session_id', 'memory_entries', ['session_id'])
    op.create_index('ix_memory_entries_context_key', 'memory_entries', ['context_key'])
    op.create_index('ix_memory_entries_expires_at', 'memory_entries', ['expires_at'])
    # Composite index for common queries
    op.create_index('ix_memory_entries_agent_session', 'memory_entries', ['agent_id', 'session_id'])
    # GIN index for JSONB content
    op.execute('CREATE INDEX ix_memory_entries_content ON memory_entries USING GIN (content)')
    
    # Create memory_associations table
    op.create_table(
        'memory_associations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('related_memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('association_type', sa.String(50), nullable=False),
        sa.Column('strength', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['memory_id'], ['agent_memories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_memory_id'], ['agent_memories.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('memory_id', 'related_memory_id', name='uq_memory_associations_pair'),
    )
    op.create_index('ix_memory_associations_memory_id', 'memory_associations', ['memory_id'])
    op.create_index('ix_memory_associations_related_id', 'memory_associations', ['related_memory_id'])
    op.create_index('ix_memory_associations_type', 'memory_associations', ['association_type'])


def downgrade():
    op.drop_index('ix_memory_associations_type', table_name='memory_associations')
    op.drop_index('ix_memory_associations_related_id', table_name='memory_associations')
    op.drop_index('ix_memory_associations_memory_id', table_name='memory_associations')
    op.drop_table('memory_associations')
    
    op.execute('DROP INDEX IF EXISTS ix_memory_entries_content')
    op.drop_index('ix_memory_entries_agent_session', table_name='memory_entries')
    op.drop_index('ix_memory_entries_expires_at', table_name='memory_entries')
    op.drop_index('ix_memory_entries_context_key', table_name='memory_entries')
    op.drop_index('ix_memory_entries_session_id', table_name='memory_entries')
    op.drop_index('ix_memory_entries_agent_id', table_name='memory_entries')
    op.drop_table('memory_entries')
    
    op.execute('DROP INDEX IF EXISTS ix_agent_memories_tags')
    op.execute('DROP INDEX IF EXISTS ix_agent_memories_content')
    op.drop_index('ix_agent_memories_expires_at', table_name='agent_memories')
    op.drop_index('ix_agent_memories_last_accessed_at', table_name='agent_memories')
    op.drop_index('ix_agent_memories_importance', table_name='agent_memories')
    op.drop_index('ix_agent_memories_memory_type', table_name='agent_memories')
    op.drop_index('ix_agent_memories_agent_id', table_name='agent_memories')
    op.drop_table('agent_memories')

