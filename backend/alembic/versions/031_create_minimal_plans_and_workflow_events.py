"""create minimal plans and workflow_events tables

Revision ID: 031_create_minimal_plans_and_workflow_events
Revises: 9b00a9011ac1
Create Date: 2025-12-11 17:50:00.000000
"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "031"
down_revision = "9b00a9011ac1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create plans table if not exists (minimal columns required by tests)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS plans (
            id uuid PRIMARY KEY,
            task_id uuid,
            version integer,
            goal text,
            strategy jsonb,
            steps jsonb,
            alternatives jsonb,
            status varchar(50),
            current_step integer,
            estimated_duration integer,
            actual_duration integer,
            created_at timestamptz DEFAULT now(),
            approved_at timestamptz
        );
        """
    )

    # Create workflow_events table if not exists (minimal columns used in flow)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS workflow_events (
            id uuid PRIMARY KEY,
            workflow_id varchar(255),
            event_type varchar(100),
            event_source varchar(100),
            stage varchar(100),
            status varchar(50),
            message text,
            event_data jsonb,
            metadata jsonb,
            task_id uuid,
            plan_id uuid,
            tool_id uuid,
            approval_request_id uuid,
            session_id varchar(255),
            trace_id varchar(255),
            parent_event_id uuid,
            timestamp timestamptz DEFAULT now(),
            duration_ms integer
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workflow_events;")
    op.execute("DROP TABLE IF EXISTS plans;")


