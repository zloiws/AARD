-- Idempotent conversion of workflow_events.plan_id to UUID
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='workflow_events' AND column_name='plan_id')
    AND (SELECT data_type FROM information_schema.columns WHERE table_name='workflow_events' AND column_name='plan_id') <> 'uuid' THEN
        ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS plan_id_new UUID;
        UPDATE workflow_events SET plan_id_new = gen_random_uuid() WHERE plan_id_new IS NULL;
        ALTER TABLE workflow_events DROP CONSTRAINT IF EXISTS workflow_events_pkey;
        ALTER TABLE workflow_events DROP COLUMN IF EXISTS plan_id CASCADE;
        ALTER TABLE workflow_events RENAME COLUMN plan_id_new TO plan_id;
    END IF;
END$$;


