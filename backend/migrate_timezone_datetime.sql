-- Migration to add timezone support to datetime columns
-- This migration updates existing datetime columns to support timezone

-- For PostgreSQL, we need to alter the columns to use timestamptz
-- Note: This may require manual intervention if there are existing data

-- Update tasks table
ALTER TABLE tasks
ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
ALTER COLUMN updated_at TYPE TIMESTAMPTZ USING updated_at AT TIME ZONE 'UTC';

-- Update approval_requests table
ALTER TABLE approval_requests
ALTER COLUMN created_at TYPE TIMESTAMPTZ USING created_at AT TIME ZONE 'UTC',
ALTER COLUMN decision_timeout TYPE TIMESTAMPTZ USING decision_timeout AT TIME ZONE 'UTC';
