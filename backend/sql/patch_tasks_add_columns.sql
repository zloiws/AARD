-- Idempotent patch to add expected columns to tasks table used by tests
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS description TEXT,
  ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS created_by VARCHAR(255),
  ADD COLUMN IF NOT EXISTS created_by_role VARCHAR(128),
  ADD COLUMN IF NOT EXISTS approved_by VARCHAR(255),
  ADD COLUMN IF NOT EXISTS approved_by_role VARCHAR(128),
  ADD COLUMN IF NOT EXISTS autonomy_level INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS parent_task_id UUID,
  ADD COLUMN IF NOT EXISTS plan_id UUID,
  ADD COLUMN IF NOT EXISTS current_checkpoint_id UUID;
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS context JSONB;


