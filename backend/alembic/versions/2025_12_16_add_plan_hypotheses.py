"""Add plan_hypotheses and plan_hypothesis_nodes tables.

Revision ID: 20251216_plan_hypotheses
Revises: 20251215_interpretation_timeline
Create Date: 2025-12-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251216_plan_hypotheses"
down_revision = "20251215_interpretation_timeline"
branch_labels = None
depends_on = None


def upgrade():
    sql = """
CREATE TABLE IF NOT EXISTS plan_hypotheses (
  id UUID PRIMARY KEY NOT NULL,
  timeline_id UUID NOT NULL REFERENCES decision_timelines(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  lifecycle VARCHAR(32) NOT NULL DEFAULT 'draft',
  assumptions JSONB,
  risks JSONB,
  confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
  steps JSONB,
  dependencies JSONB,
  resources JSONB,
  plan_metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS plan_hypothesis_nodes (
  id UUID PRIMARY KEY NOT NULL,
  hypothesis_id UUID NOT NULL REFERENCES plan_hypotheses(id) ON DELETE CASCADE,
  node_id UUID NOT NULL REFERENCES decision_nodes(id) ON DELETE CASCADE,
  timeline_id UUID NOT NULL REFERENCES decision_timelines(id) ON DELETE CASCADE,
  node_type VARCHAR(50) NOT NULL,
  node_metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_plan_hypotheses_timeline_lifecycle ON plan_hypotheses(timeline_id, lifecycle);
CREATE INDEX IF NOT EXISTS ix_plan_hypothesis_nodes_hypothesis_node ON plan_hypothesis_nodes(hypothesis_id, node_id);
"""
    op.execute(sql)


def downgrade():
    # No-op: manual rollback required if needed.
    pass


