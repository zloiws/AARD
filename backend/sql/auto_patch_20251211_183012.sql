-- Auto-generated patch 2025-12-11T18:30:12.536072
BEGIN;

ALTER TABLE plans
  ADD COLUMN IF NOT EXISTS estimated_duration TEXT,
  ADD COLUMN IF NOT EXISTS estimated_duration TEXT;
COMMIT;
