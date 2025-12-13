-- Convert workflow_events.id from integer to uuid idempotently
DO $$
BEGIN
    PERFORM 1 FROM pg_extension WHERE extname = 'pgcrypto';
    IF NOT FOUND THEN
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    END IF;
END$$;

DO $$
BEGIN
    IF (SELECT data_type FROM information_schema.columns WHERE table_name='workflow_events' AND column_name='id') <> 'uuid' THEN
        ALTER TABLE workflow_events ADD COLUMN IF NOT EXISTS id_new UUID DEFAULT gen_random_uuid();
        UPDATE workflow_events SET id_new = gen_random_uuid() WHERE id_new IS NULL;
        -- drop existing pk if exists
        ALTER TABLE workflow_events DROP CONSTRAINT IF EXISTS workflow_events_pkey;
        -- drop old id column
        ALTER TABLE workflow_events DROP COLUMN IF EXISTS id CASCADE;
        -- rename and set pk
        ALTER TABLE workflow_events RENAME COLUMN id_new TO id;
        ALTER TABLE workflow_events ADD PRIMARY KEY (id);
    END IF;
END$$;



