-- Planning Hypothesis Tables for AARD
-- Execute this in your PostgreSQL database

-- plan_hypotheses
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

-- plan_hypothesis_nodes
CREATE TABLE IF NOT EXISTS plan_hypothesis_nodes (
  id UUID PRIMARY KEY NOT NULL,
  hypothesis_id UUID NOT NULL REFERENCES plan_hypotheses(id) ON DELETE CASCADE,
  node_id UUID NOT NULL REFERENCES decision_nodes(id) ON DELETE CASCADE,
  node_type VARCHAR(50) NOT NULL,
  node_metadata JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- indexes
CREATE INDEX IF NOT EXISTS ix_plan_hypotheses_timeline_lifecycle ON plan_hypotheses(timeline_id, lifecycle);
CREATE INDEX IF NOT EXISTS ix_plan_hypothesis_nodes_hypothesis_node ON plan_hypothesis_nodes(hypothesis_id, node_id);

-- Check tables were created
SELECT 'plan_hypotheses' as table_name, COUNT(*) as record_count FROM plan_hypotheses
UNION ALL
SELECT 'plan_hypothesis_nodes' as table_name, COUNT(*) as record_count FROM plan_hypothesis_nodes;
