"""add ollama servers and models tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ollama_servers table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.ollama_servers')")).scalar():
        op.create_table('ollama_servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('url', sa.String(500), nullable=False),
        sa.Column('api_version', sa.String(10), nullable=False, server_default='v1'),
        sa.Column('auth_type', sa.String(50), nullable=True),
        sa.Column('auth_config', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('capabilities', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('max_concurrent', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_checked_at', sa.DateTime(), nullable=True),
        sa.Column('is_available', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('server_metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint('name', name='uq_ollama_servers_name'),
        sa.UniqueConstraint('url', name='uq_ollama_servers_url'),
    )
    
    # Create indexes for ollama_servers
    op.execute("CREATE INDEX IF NOT EXISTS idx_ollama_servers_active ON ollama_servers (is_active);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ollama_servers_default ON ollama_servers (is_default);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ollama_servers_priority ON ollama_servers (priority);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ollama_servers_available ON ollama_servers (is_available);")
    
    # Create ollama_models table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.ollama_models')")).scalar():
        op.create_table('ollama_models',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('server_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('model_name', sa.String(255), nullable=False),
        sa.Column('digest', sa.String(255), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('format', sa.String(50), nullable=True),
        sa.Column('modified_at', sa.DateTime(), nullable=True),
        sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('capabilities', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['server_id'], ['ollama_servers.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for ollama_models
    op.execute("CREATE INDEX IF NOT EXISTS idx_ollama_models_server ON ollama_models (server_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ollama_models_active ON ollama_models (is_active);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_ollama_models_name ON ollama_models (model_name);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_ollama_models_server_name ON ollama_models (server_id, model_name);")


def downgrade() -> None:
    op.drop_index('idx_ollama_models_server_name', table_name='ollama_models')
    op.drop_index('idx_ollama_models_name', table_name='ollama_models')
    op.drop_index('idx_ollama_models_active', table_name='ollama_models')
    op.drop_index('idx_ollama_models_server', table_name='ollama_models')
    op.drop_table('ollama_models')
    op.drop_index('idx_ollama_servers_available', table_name='ollama_servers')
    op.drop_index('idx_ollama_servers_priority', table_name='ollama_servers')
    op.drop_index('idx_ollama_servers_default', table_name='ollama_servers')
    op.drop_index('idx_ollama_servers_active', table_name='ollama_servers')
    op.drop_table('ollama_servers')

