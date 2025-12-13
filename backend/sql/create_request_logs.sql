-- Create request_logs and request_consequences tables idempotently
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS request_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_type TEXT NOT NULL,
  request_data JSONB NOT NULL,
  model_used TEXT,
  server_url TEXT,
  status TEXT NOT NULL,
  response_data JSONB,
  error_message TEXT,
  duration_ms INTEGER,
  created_artifacts UUID[],
  created_plans UUID[],
  created_approvals UUID[],
  modified_artifacts UUID[],
  success_score DOUBLE PRECISION DEFAULT 0.5 NOT NULL,
  importance_score DOUBLE PRECISION DEFAULT 0.5 NOT NULL,
  impact_score DOUBLE PRECISION DEFAULT 0.5 NOT NULL,
  overall_rank DOUBLE PRECISION DEFAULT 0.5 NOT NULL,
  user_id TEXT,
  session_id TEXT,
  trace_id TEXT,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_request_logs_status ON request_logs(status);
CREATE INDEX IF NOT EXISTS idx_request_logs_type ON request_logs(request_type);
CREATE INDEX IF NOT EXISTS idx_request_logs_rank ON request_logs(overall_rank);
CREATE INDEX IF NOT EXISTS idx_request_logs_created_at ON request_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_request_logs_model ON request_logs(model_used);
CREATE INDEX IF NOT EXISTS idx_request_logs_trace_id ON request_logs(trace_id);

CREATE TABLE IF NOT EXISTS request_consequences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID REFERENCES request_logs(id) ON DELETE CASCADE,
  consequence_type TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id UUID NOT NULL,
  impact_type TEXT,
  impact_description TEXT,
  impact_score DOUBLE PRECISION DEFAULT 0.0 NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_consequences_request ON request_consequences(request_id);
CREATE INDEX IF NOT EXISTS idx_consequences_entity ON request_consequences(entity_type, entity_id);


