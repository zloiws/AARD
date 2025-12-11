"""Add tools table

Revision ID: 010_add_tools
Revises: 009_add_agents
Create Date: 2025-12-03 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '010_add_tools'
down_revision = '009_add_agents'
branch_labels = None
depends_on = None


def upgrade():
    # Create tools table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.tools')")).scalar():
        op.create_table('tools',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(50), nullable=True),
        
        # Versioning
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('parent_tool_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        # Status and lifecycle
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('activated_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        
        # Tool implementation
        sa.Column('code', sa.Text(), nullable=True),
        sa.Column('entry_point', sa.String(255), nullable=True),
        sa.Column('language', sa.String(50), nullable=False, server_default='python'),
        
        # Tool schema
        sa.Column('input_schema', postgresql.JSONB(), nullable=True),
        sa.Column('output_schema', postgresql.JSONB(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        
        # Dependencies
        sa.Column('dependencies', postgresql.JSONB(), nullable=True),
        sa.Column('requirements', sa.Text(), nullable=True),
        
        # Security
        sa.Column('security_policies', postgresql.JSONB(), nullable=True),
        sa.Column('allowed_agents', postgresql.JSONB(), nullable=True),
        sa.Column('forbidden_agents', postgresql.JSONB(), nullable=True),
        sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='false'),
        
        # Resource limits
        sa.Column('timeout_seconds', sa.Integer(), nullable=True),
        sa.Column('max_memory_mb', sa.Integer(), nullable=True),
        sa.Column('rate_limit_per_minute', sa.Integer(), nullable=True),
        
        # Metrics
        sa.Column('total_executions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_executions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_executions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('average_execution_time', sa.Integer(), nullable=True),
        sa.Column('success_rate', sa.String(10), nullable=True),
        
        # Metadata (renamed to tool_metadata to avoid SQLAlchemy reserved name)
        sa.Column('tool_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('examples', postgresql.JSONB(), nullable=True),
    )
    
    # Add foreign key
    op.create_foreign_key(
        'fk_tools_parent_tool_id',
        'tools', 'tools',
        ['parent_tool_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create indexes
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_tools_name ON tools (name);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tools_status ON tools (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tools_category ON tools (category);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tools_created_at ON tools (created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_tools_tags ON tools (tags);")


def downgrade():
    op.drop_index('ix_tools_tags', table_name='tools')
    op.drop_index('ix_tools_created_at', table_name='tools')
    op.drop_index('ix_tools_category', table_name='tools')
    op.drop_index('ix_tools_status', table_name='tools')
    op.drop_index('ix_tools_name', table_name='tools')
    op.drop_table('tools')

