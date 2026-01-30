-- init.sql
-- PostgreSQL initialization script for Maintenance Service API
-- This script runs automatically when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges (the database and user are created automatically by PostgreSQL image)
-- These are additional configurations if needed

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully!';
END $$;
