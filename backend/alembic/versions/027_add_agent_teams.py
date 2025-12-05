"""Add agent teams

Revision ID: 027_add_agent_teams
Revises: 026_add_plan_templates
Create Date: 2025-12-05 21:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '027_add_agent_teams'
down_revision = '026_add_plan_templates'
branch_labels = None
depends_on = None


def upgrade():
    # Create agent_teams table
    op.create_table(
        'agent_teams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        
        # Team configuration
        sa.Column('roles', postgresql.JSONB(), nullable=True),
        sa.Column('coordination_strategy', sa.String(50), nullable=False, server_default='collaborative'),
        
        # Status and lifecycle
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        
        # Metadata
        sa.Column('team_metadata', postgresql.JSONB(), nullable=True),
    )
    
    # Create agent_team_associations table (many-to-many relationship)
    op.create_table(
        'agent_team_associations',
        sa.Column('team_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_teams.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(100), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_lead', sa.Boolean(), nullable=False, server_default='false'),
    )
    
    # Create indexes
    op.create_index('ix_agent_teams_name', 'agent_teams', ['name'], unique=True)
    op.create_index('ix_agent_teams_status', 'agent_teams', ['status'])
    op.create_index('ix_agent_team_associations_team_id', 'agent_team_associations', ['team_id'])
    op.create_index('ix_agent_team_associations_agent_id', 'agent_team_associations', ['agent_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_agent_team_associations_agent_id', table_name='agent_team_associations')
    op.drop_index('ix_agent_team_associations_team_id', table_name='agent_team_associations')
    op.drop_index('ix_agent_teams_status', table_name='agent_teams')
    op.drop_index('ix_agent_teams_name', table_name='agent_teams')
    
    # Drop tables
    op.drop_table('agent_team_associations')
    op.drop_table('agent_teams')

