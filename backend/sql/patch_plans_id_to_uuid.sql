-- Convert plans.id from integer to uuid idempotently
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='plans' AND column_name='id')
    AND (SELECT data_type FROM information_schema.columns WHERE table_name='plans' AND column_name='id') <> 'uuid' THEN
        PERFORM 1 FROM pg_extension WHERE extname = 'pgcrypto';
        IF NOT FOUND THEN
            CREATE EXTENSION IF NOT EXISTS pgcrypto;
        END IF;
        ALTER TABLE plans ADD COLUMN IF NOT EXISTS id_new UUID DEFAULT gen_random_uuid();
        UPDATE plans SET id_new = gen_random_uuid() WHERE id_new IS NULL;
        ALTER TABLE plans DROP CONSTRAINT IF EXISTS plans_pkey;
        ALTER TABLE plans DROP COLUMN IF EXISTS id CASCADE;
        ALTER TABLE plans RENAME COLUMN id_new TO id;
        ALTER TABLE plans ADD PRIMARY KEY (id);
    END IF;
END$$;


