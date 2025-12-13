-- Create project_metrics table idempotently
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS project_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  metric_type TEXT NOT NULL,
  metric_name TEXT NOT NULL,
  period TEXT NOT NULL,
  period_start TIMESTAMPTZ NOT NULL,
  period_end TIMESTAMPTZ NOT NULL,
  value DOUBLE PRECISION,
  count INTEGER DEFAULT 0 NOT NULL,
  min_value DOUBLE PRECISION,
  max_value DOUBLE PRECISION,
  sum_value DOUBLE PRECISION,
  metric_metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_project_metrics_type_name_period ON project_metrics(metric_type, metric_name, period);
CREATE INDEX IF NOT EXISTS idx_project_metrics_period_start ON project_metrics(period_start);


