-- Create read-only user for code executor
-- This script is run automatically when the postgres container starts

-- Create user for code executor (read-only)
CREATE USER code_executor_readonly WITH PASSWORD 'readonly_secure_password';

-- Grant connection to database
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

