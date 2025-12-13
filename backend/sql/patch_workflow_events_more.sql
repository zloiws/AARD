-- Add remaining workflow_events columns idempotently
ALTER TABLE workflow_events
  ADD COLUMN IF NOT EXISTS tool_id UUID,
  ADD COLUMN IF NOT EXISTS approval_request_id UUID,
  ADD COLUMN IF NOT EXISTS session_id TEXT,
  ADD COLUMN IF NOT EXISTS trace_id TEXT;


