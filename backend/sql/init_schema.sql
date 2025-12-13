-- Idempotent initial schema for AARD project
-- Use: psql -d $DB -f backend/sql/init_schema.sql
BEGIN;

-- ollama_servers
CREATE TABLE IF NOT EXISTS ollama_servers (
  id SERIAL PRIMARY KEY,
  url VARCHAR(255) UNIQUE,
  name VARCHAR(255),
  host VARCHAR(255),
  is_active BOOLEAN DEFAULT true,
  server_metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ollama_models
CREATE TABLE IF NOT EXISTS ollama_models (
  id SERIAL PRIMARY KEY,
  server_id INTEGER REFERENCES ollama_servers(id) ON DELETE SET NULL,
  model_name VARCHAR(255) NOT NULL,
  name VARCHAR(255),
  is_active BOOLEAN DEFAULT true,
  details JSONB,
  digest VARCHAR(255),
  size_bytes BIGINT,
  format VARCHAR(64),
  modified_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (server_id, model_name)
);

-- agents
CREATE TABLE IF NOT EXISTS agents (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- tools
CREATE TABLE IF NOT EXISTS tools (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255) UNIQUE,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- tasks
CREATE TABLE IF NOT EXISTS tasks (
  id SERIAL PRIMARY KEY,
  name VARCHAR(255),
  status VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- plans
CREATE TABLE IF NOT EXISTS plans (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255),
  data JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- workflow_events
CREATE TABLE IF NOT EXISTS workflow_events (
  id SERIAL PRIMARY KEY,
  plan_id INTEGER REFERENCES plans(id) ON DELETE CASCADE,
  event_type VARCHAR(255),
  payload JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- agent_memories (includes embedding array column)
CREATE TABLE IF NOT EXISTS agent_memories (
  id SERIAL PRIMARY KEY,
  agent_id INTEGER REFERENCES agents(id) ON DELETE CASCADE,
  memory JSONB,
  embedding DOUBLE PRECISION[],
  created_at TIMESTAMPTZ DEFAULT now()
);

-- alembic_version (ensure existence for projects that use alembic)
CREATE TABLE IF NOT EXISTS alembic_version (
  version_num VARCHAR(64) PRIMARY KEY
);

COMMIT;


