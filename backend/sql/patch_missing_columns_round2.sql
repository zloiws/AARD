-- Add commonly referenced missing columns (idempotent)
ALTER TABLE workflow_events
  ADD COLUMN IF NOT EXISTS workflow_id UUID,
  ADD COLUMN IF NOT EXISTS event_source TEXT,
  ADD COLUMN IF NOT EXISTS stage TEXT,
  ADD COLUMN IF NOT EXISTS status TEXT,
  ADD COLUMN IF NOT EXISTS message TEXT,
  ADD COLUMN IF NOT EXISTS event_data JSONB,
  ADD COLUMN IF NOT EXISTS metadata JSONB,
  ADD COLUMN IF NOT EXISTS timestamp TIMESTAMPTZ DEFAULT now(),
  ADD COLUMN IF NOT EXISTS duration_ms INTEGER;

ALTER TABLE prompts
  ADD COLUMN IF NOT EXISTS user_rating DOUBLE PRECISION;

-- Ensure plan_templates exists (if not, create minimal)
CREATE TABLE IF NOT EXISTS plan_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid()
);


