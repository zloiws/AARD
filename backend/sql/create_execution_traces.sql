-- Create execution_traces table idempotently
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS execution_traces (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id TEXT UNIQUE NOT NULL,
  task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
  plan_id UUID REFERENCES plans(id) ON DELETE SET NULL,
  span_id TEXT,
  parent_span_id TEXT,
  operation_name TEXT NOT NULL,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  duration_ms INTEGER,
  status TEXT,
  attributes JSONB,
  agent_id UUID,
  tool_id UUID,
  error_message TEXT,
  error_type TEXT,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_traces_trace_id ON execution_traces(trace_id);
CREATE INDEX IF NOT EXISTS idx_traces_task_id ON execution_traces(task_id);
CREATE INDEX IF NOT EXISTS idx_traces_plan_id ON execution_traces(plan_id);
CREATE INDEX IF NOT EXISTS idx_traces_agent_id ON execution_traces(agent_id);
CREATE INDEX IF NOT EXISTS idx_traces_start_time ON execution_traces(start_time);
CREATE INDEX IF NOT EXISTS idx_traces_status ON execution_traces(status);
CREATE INDEX IF NOT EXISTS idx_traces_operation ON execution_traces(operation_name);


