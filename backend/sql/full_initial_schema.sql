-- Comprehensive idempotent full initial schema for AARD
-- Use: psql -d $DB -f backend/sql/full_initial_schema.sql
BEGIN;

-- Ensure extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- alembic_version
CREATE TABLE IF NOT EXISTS alembic_version (
  version_num VARCHAR(64) PRIMARY KEY
);

-- ollama_servers
CREATE TABLE IF NOT EXISTS ollama_servers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url TEXT UNIQUE,
  name TEXT,
  host TEXT,
  api_version TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  is_default BOOLEAN DEFAULT FALSE,
  description TEXT,
  capabilities JSONB,
  max_concurrent INTEGER DEFAULT 1,
  priority INTEGER DEFAULT 0,
  server_metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ
);

-- ollama_models
CREATE TABLE IF NOT EXISTS ollama_models (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  server_id UUID REFERENCES ollama_servers(id) ON DELETE SET NULL,
  model_name TEXT NOT NULL,
  name TEXT,
  model TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  details JSONB,
  capabilities JSONB,
  digest TEXT,
  size_bytes BIGINT,
  format TEXT,
  modified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ,
  last_seen_at TIMESTAMPTZ,
  priority INTEGER DEFAULT 0,
  UNIQUE (server_id, model_name)
);

-- agents
CREATE TABLE IF NOT EXISTS agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE,
  description TEXT,
  version VARCHAR(64),
  parent_agent_id UUID,
  status VARCHAR(50),
  created_by VARCHAR(255),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ,
  activated_at TIMESTAMPTZ,
  last_used_at TIMESTAMPTZ,
  endpoint TEXT,
  last_heartbeat TIMESTAMPTZ,
  health_status VARCHAR(50),
  last_health_check TIMESTAMPTZ,
  response_time_ms INTEGER,
  system_prompt TEXT,
  capabilities JSONB,
  model_preference VARCHAR(255),
  temperature DOUBLE PRECISION,
  identity_id VARCHAR(255),
  security_policies JSONB,
  allowed_actions JSONB,
  forbidden_actions JSONB,
  max_concurrent_tasks INTEGER,
  rate_limit_per_minute INTEGER,
  memory_limit_mb INTEGER,
  total_tasks_executed INTEGER DEFAULT 0,
  successful_tasks INTEGER DEFAULT 0,
  failed_tasks INTEGER DEFAULT 0,
  average_execution_time DOUBLE PRECISION,
  success_rate DOUBLE PRECISION,
  agent_metadata JSONB,
  tags TEXT[]
);

-- tools
CREATE TABLE IF NOT EXISTS tools (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- prompts
CREATE TABLE IF NOT EXISTS prompts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT,
  prompt_text TEXT,
  prompt_type TEXT,
  level INTEGER DEFAULT 0,
  version INTEGER DEFAULT 1,
  parent_prompt_id UUID,
  status VARCHAR(50) DEFAULT 'active',
  success_rate DOUBLE PRECISION,
  avg_execution_time DOUBLE PRECISION,
  usage_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  created_by VARCHAR(255),
  last_improved_at TIMESTAMPTZ,
  improvement_history JSONB
);

-- plan_templates
CREATE TABLE IF NOT EXISTS plan_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT,
  description TEXT,
  category TEXT,
  tags TEXT[],
  goal_pattern TEXT,
  strategy_template TEXT,
  steps_template TEXT,
  alternatives_template TEXT,
  status VARCHAR(50) DEFAULT 'active',
  version INTEGER DEFAULT 1,
  success_rate DOUBLE PRECISION,
  avg_execution_time DOUBLE PRECISION,
  usage_count INTEGER DEFAULT 0,
  source_plan_ids UUID[],
  source_task_descriptions TEXT[],
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ,
  last_used_at TIMESTAMPTZ
);

-- plans
CREATE TABLE IF NOT EXISTS plans (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT,
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ
);

-- tasks
CREATE TABLE IF NOT EXISTS tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  description TEXT,
  status VARCHAR(50),
  priority INTEGER DEFAULT 0,
  created_by VARCHAR(255),
  created_by_role VARCHAR(128),
  approved_by VARCHAR(255),
  approved_by_role VARCHAR(128),
  autonomy_level INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ,
  parent_task_id UUID,
  plan_id UUID,
  current_checkpoint_id UUID,
  context JSONB
);

-- workflow_events
CREATE TABLE IF NOT EXISTS workflow_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workflow_id UUID,
  event_type TEXT,
  event_source TEXT,
  stage TEXT,
  status TEXT,
  message TEXT,
  event_data JSONB,
  metadata JSONB,
  task_id UUID,
  plan_id UUID,
  tool_id UUID,
  approval_request_id UUID,
  session_id TEXT,
  trace_id TEXT,
  parent_event_id UUID,
  timestamp TIMESTAMPTZ DEFAULT now(),
  duration_ms INTEGER
);

-- plan_templates vector/index tables (optional)
CREATE TABLE IF NOT EXISTS benchmark_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  benchmark_task_id UUID,
  model_id UUID,
  server_id UUID,
  execution_time DOUBLE PRECISION,
  output TEXT,
  score DOUBLE PRECISION,
  metrics JSONB,
  passed BOOLEAN,
  error_message TEXT,
  execution_metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- agent_memories
CREATE TABLE IF NOT EXISTS agent_memories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
  memory JSONB,
  embedding DOUBLE PRECISION[],
  created_at TIMESTAMPTZ DEFAULT now()
);

-- indexes for common lookups
CREATE INDEX IF NOT EXISTS idx_ollama_servers_url ON ollama_servers(url);
CREATE INDEX IF NOT EXISTS idx_ollama_models_server_model ON ollama_models(server_id, model_name);
CREATE INDEX IF NOT EXISTS idx_tasks_plan_id ON tasks(plan_id);
-- Ensure workflow_events columns exist before creating index (handles existing table without columns)
ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS task_id UUID;
ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS plan_id UUID;
ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS parent_event_id UUID;
CREATE INDEX IF NOT EXISTS idx_workflow_events_task_id ON workflow_events(task_id);

COMMIT;


