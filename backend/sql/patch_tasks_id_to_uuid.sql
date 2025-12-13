-- Convert tasks.id from integer to uuid in an idempotent way.
-- Steps:
-- 1. Ensure pgcrypto extension for gen_random_uuid()
-- 2. Add id_new UUID column with gen_random_uuid() default
-- 3. Populate id_new for existing rows
-- 4. Drop primary key constraint and old id column
-- 5. Rename id_new to id and add primary key
DO $$
BEGIN
    -- Ensure extension
    PERFORM 1 FROM pg_extension WHERE extname = 'pgcrypto';
    IF NOT FOUND THEN
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    END IF;
END$$;

-- If id column is already UUID, do nothing
DO $$
BEGIN
    IF (SELECT data_type FROM information_schema.columns WHERE table_name='tasks' AND column_name='id') <> 'uuid' THEN
        -- Add new uuid column
        ALTER TABLE tasks ADD COLUMN IF NOT EXISTS id_new UUID DEFAULT gen_random_uuid();
        -- Populate any NULLs
        UPDATE tasks SET id_new = gen_random_uuid() WHERE id_new IS NULL;

        -- Drop existing primary key constraint if present
        IF EXISTS (
            SELECT 1 FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            WHERE t.relname = 'tasks' AND c.contype = 'p'
        ) THEN
            ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_pkey;
        END IF;

        -- Drop old id column
        ALTER TABLE tasks DROP COLUMN IF EXISTS id CASCADE;
        -- Rename new column to id
        ALTER TABLE tasks RENAME COLUMN id_new TO id;
        -- Add primary key on id
        ALTER TABLE tasks ADD PRIMARY KEY (id);
    END IF;
END$$;


