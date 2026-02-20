-- Maritime Intelligence Engine Database Initialization
-- PostgreSQL initialization script for Docker deployment

-- Create extensions if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create schema for better organization (optional)
-- CREATE SCHEMA IF NOT EXISTS maritime_intelligence;
-- SET search_path TO maritime_intelligence, public;

-- The actual tables will be created by SQLAlchemy models
-- This script just ensures necessary extensions and initial setup

-- Create indexes for performance (these will be created by SQLAlchemy but included here for reference)
-- Index comments for future reference:

-- Articles table indexes:
-- - url for deduplication checks
-- - publication_date for date range queries
-- - category and severity for filtering
-- - ports and vessels using GIN indexes for array searches

-- Workflow runs table indexes:
-- - run_date for chronological queries
-- - status for filtering active/completed runs

-- Performance optimization settings
-- These can be adjusted based on deployment needs

-- Increase shared memory for better performance
-- ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
-- ALTER SYSTEM SET shared_buffers = '256MB';
-- ALTER SYSTEM SET effective_cache_size = '1GB';
-- ALTER SYSTEM SET maintenance_work_mem = '64MB';
-- ALTER SYSTEM SET checkpoint_completion_target = 0.9;
-- ALTER SYSTEM SET wal_buffers = '16MB';
-- ALTER SYSTEM SET default_statistics_target = 100;

-- Note: System-level changes require PostgreSQL restart
-- These are commented out as they require superuser privileges

-- Create a function to update the updated_at timestamp (useful for audit trails)
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Maritime Intelligence Engine database initialization completed successfully';
END $$;