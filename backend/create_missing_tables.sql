-- Create missing tables that are causing test failures
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Checkpoints table
CREATE TABLE IF NOT EXISTS checkpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type VARCHAR(50) NOT NULL,
  entity_id UUID NOT NULL,
  state_data JSONB NOT NULL,
  state_hash VARCHAR(64),
  reason VARCHAR(255),
  created_by VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  request_id UUID REFERENCES request_logs(id) ON DELETE SET NULL,
  trace_id VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_entity ON checkpoints(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_created ON checkpoints(created_at);
CREATE INDEX IF NOT EXISTS idx_checkpoints_state_hash ON checkpoints(state_hash);
CREATE INDEX IF NOT EXISTS idx_checkpoints_trace_id ON checkpoints(trace_id);

-- Approval requests table
CREATE TABLE IF NOT EXISTS approval_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_type VARCHAR(50) NOT NULL,
  artifact_id UUID REFERENCES artifacts(id) ON DELETE CASCADE,
  prompt_id UUID REFERENCES prompts(id) ON DELETE CASCADE,
  task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
  plan_id UUID REFERENCES plans(id) ON DELETE CASCADE,
  request_data JSON NOT NULL,
  risk_assessment JSON,
  recommendation TEXT,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  required_action VARCHAR(20),
  human_feedback TEXT,
  approved_by VARCHAR(255),
  approved_at TIMESTAMPTZ,
  decision_timeout TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Evolution history table
CREATE TABLE IF NOT EXISTS evolution_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type VARCHAR(50) NOT NULL,
  entity_id UUID NOT NULL,
  change_type VARCHAR(50),
  change_description TEXT,
  before_state JSON,
  after_state JSON,
  trigger_type VARCHAR(50),
  trigger_data JSON,
  improvement_metrics JSON,
  success BOOLEAN,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Feedback table
CREATE TABLE IF NOT EXISTS feedback (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type VARCHAR(50) NOT NULL,
  entity_id UUID NOT NULL,
  feedback_type VARCHAR(50),
  rating INTEGER,
  comment TEXT,
  task_id UUID REFERENCES tasks(id) ON DELETE SET NULL,
  session_id VARCHAR(255),
  processed BOOLEAN NOT NULL DEFAULT false,
  insights_extracted JSON,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_approval_requests_status ON approval_requests(status);
CREATE INDEX IF NOT EXISTS idx_approval_requests_type ON approval_requests(request_type);
CREATE INDEX IF NOT EXISTS idx_approval_requests_created ON approval_requests(created_at);

CREATE INDEX IF NOT EXISTS idx_evolution_history_entity ON evolution_history(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_evolution_history_created ON evolution_history(created_at);

CREATE INDEX IF NOT EXISTS idx_feedback_entity ON feedback(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_feedback_task ON feedback(task_id);
CREATE INDEX IF NOT EXISTS idx_feedback_processed ON feedback(processed);
