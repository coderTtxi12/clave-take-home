-- Create read-only user for code executor
-- This script creates a read-only user for the code executor service
-- Safe to run multiple times (uses IF NOT EXISTS pattern)

-- Create user for code executor (read-only)
-- Note: PostgreSQL doesn't support IF NOT EXISTS for CREATE USER, so we use DO block
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = 'code_executor_readonly') THEN
        CREATE USER code_executor_readonly WITH PASSWORD 'readonly_secure_password';
    ELSE
        -- Update password if user exists (optional, comment out if you want to keep existing password)
        -- ALTER USER code_executor_readonly WITH PASSWORD 'readonly_secure_password';
        RAISE NOTICE 'User code_executor_readonly already exists, skipping creation';
    END IF;
END
$$;

-- Grant connection to database
-- Note: Database name will be replaced by setup script (postgres for Supabase, restaurant_analytics for local)
GRANT CONNECT ON DATABASE restaurant_analytics TO code_executor_readonly;

-- Grant usage on public schema
GRANT USAGE ON SCHEMA public TO code_executor_readonly;

-- Grant SELECT on all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO code_executor_readonly;

-- Grant SELECT on all future tables (for new tables created later)
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT SELECT ON TABLES TO code_executor_readonly;

-- Grant usage on sequences (for serial columns in SELECT queries)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO code_executor_readonly;

-- Optional: Grant execution on functions (if needed for queries)
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO code_executor_readonly;

-- Verify permissions
\du code_executor_readonly
\l restaurant_analytics

