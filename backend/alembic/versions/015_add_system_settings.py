"""add system settings table

Revision ID: 015
Revises: 014
Create Date: 2025-01-12 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '029'
down_revision: Union[str, None] = '028_add_agent_conversations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create system_settings table
    conn = op.get_bind()
    if not conn.execute(sa.text("select to_regclass('public.system_settings')")).scalar():
        op.create_table('system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(255), unique=True, nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(20), nullable=False, server_default='string'),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('module', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_by', sa.String(255), nullable=True),
    )
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_system_settings_key ON system_settings (key);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_system_settings_category ON system_settings (category);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_system_settings_module ON system_settings (module);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_settings_category_active ON system_settings (category, is_active);")


def downgrade() -> None:
    op.drop_index('idx_settings_category_active', 'system_settings')
    op.drop_index('idx_system_settings_module', 'system_settings')
    op.drop_index('idx_system_settings_category', 'system_settings')
    op.drop_index('idx_system_settings_key', 'system_settings')
    op.drop_table('system_settings')

