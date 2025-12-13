-- Auto-generated patch 2025-12-11T18:30:18.330308
BEGIN;

ALTER TABLE plans
  ADD COLUMN IF NOT EXISTS actual_duration TEXT,
  ADD COLUMN IF NOT EXISTS actual_duration TEXT;
COMMIT;
