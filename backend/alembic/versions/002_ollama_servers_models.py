"""add ollama servers and models tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ollama_servers table
    op.create_table(
        'ollama_servers',
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
    op.create_index('idx_ollama_servers_active', 'ollama_servers', ['is_active'])
    op.create_index('idx_ollama_servers_default', 'ollama_servers', ['is_default'])
    op.create_index('idx_ollama_servers_priority', 'ollama_servers', ['priority'])
    op.create_index('idx_ollama_servers_available', 'ollama_servers', ['is_available'])
    
    # Create ollama_models table
    op.create_table(
        'ollama_models',
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
    op.create_index('idx_ollama_models_server', 'ollama_models', ['server_id'])
    op.create_index('idx_ollama_models_active', 'ollama_models', ['is_active'])
    op.create_index('idx_ollama_models_name', 'ollama_models', ['model_name'])
    op.create_index('idx_ollama_models_server_name', 'ollama_models', ['server_id', 'model_name'], unique=True)


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

