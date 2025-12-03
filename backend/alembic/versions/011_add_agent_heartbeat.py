"""Add heartbeat and health fields to agents

Revision ID: 011_add_agent_heartbeat
Revises: 010_add_tools
Create Date: 2025-12-03 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '011_add_agent_heartbeat'
down_revision = '010_add_tools'
branch_labels = None
depends_on = None


def upgrade():
    # Add heartbeat and health fields to agents table
    op.add_column('agents', sa.Column('endpoint', sa.String(255), nullable=True))
    op.add_column('agents', sa.Column('last_heartbeat', sa.DateTime(), nullable=True))
    op.add_column('agents', sa.Column('health_status', sa.String(50), nullable=True, server_default='unknown'))
    op.add_column('agents', sa.Column('last_health_check', sa.DateTime(), nullable=True))
    op.add_column('agents', sa.Column('response_time_ms', sa.Integer(), nullable=True))
    
    # Create index for health status
    op.create_index('ix_agents_health_status', 'agents', ['health_status'])
    op.create_index('ix_agents_last_heartbeat', 'agents', ['last_heartbeat'])


def downgrade():
    op.drop_index('ix_agents_last_heartbeat', table_name='agents')
    op.drop_index('ix_agents_health_status', table_name='agents')
    op.drop_column('agents', 'response_time_ms')
    op.drop_column('agents', 'last_health_check')
    op.drop_column('agents', 'health_status')
    op.drop_column('agents', 'last_heartbeat')
    op.drop_column('agents', 'endpoint')

