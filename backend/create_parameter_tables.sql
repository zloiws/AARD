-- Create uncertainty_parameters table
CREATE TABLE IF NOT EXISTS uncertainty_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parameter_name VARCHAR(255) UNIQUE NOT NULL,
    parameter_type VARCHAR(50) NOT NULL,
    numeric_value FLOAT,
    text_value TEXT,
    json_value JSONB,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    learning_history JSONB,
    performance_metrics JSONB,
    last_improved_at TIMESTAMP WITH TIME ZONE,
    improvement_count INTEGER NOT NULL DEFAULT 0,
    description TEXT
);

CREATE INDEX IF NOT EXISTS ix_uncertainty_parameters_parameter_name ON uncertainty_parameters(parameter_name);

-- Create parameter type enum if not exists
DO $$ BEGIN
    CREATE TYPE parametertype AS ENUM ('weight', 'threshold', 'keyword_list', 'count_threshold', 'similarity_threshold');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Create system_parameters table
CREATE TABLE IF NOT EXISTS system_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parameter_name VARCHAR(255) NOT NULL,
    category VARCHAR(50) NOT NULL,
    parameter_type VARCHAR(50) NOT NULL,
    numeric_value FLOAT,
    text_value TEXT,
    json_value JSONB,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    learning_history JSONB,
    performance_metrics JSONB,
    last_improved_at TIMESTAMP WITH TIME ZONE,
    improvement_count INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    extra_metadata JSONB
);

CREATE INDEX IF NOT EXISTS ix_system_parameters_parameter_name ON system_parameters(parameter_name);
CREATE INDEX IF NOT EXISTS ix_system_parameters_category ON system_parameters(category);

-- Create enums if not exists
DO $$ BEGIN
    CREATE TYPE parametercategory AS ENUM ('uncertainty', 'approval', 'critic', 'conflict_resolution', 'quota', 'planning', 'memory', 'execution', 'meta_learning');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE systemparametertype AS ENUM ('weight', 'threshold', 'keyword_list', 'count_threshold', 'similarity_threshold', 'penalty', 'bonus');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

