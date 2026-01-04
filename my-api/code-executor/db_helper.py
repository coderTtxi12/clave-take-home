"""
Database connection helper for code executor
Provides READ-ONLY access to restaurant analytics database

⚠️ IMPORTANT: This connection uses a READ-ONLY user.
Only SELECT queries are allowed. INSERT/UPDATE/DELETE will fail.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from typing import Optional

# Database connection parameters from environment
# Prefers Supabase if configured, otherwise uses local PostgreSQL
# For Supabase, uses the main user (read-only can be configured via RLS policies)
# For local, uses READ-ONLY user: code_executor_readonly
def get_db_config():
    """Get database configuration, preferring Supabase if configured"""
    supabase_host = os.getenv('SUPABASE_DB_HOST')
    if supabase_host:
        return {
            'host': supabase_host,
            'port': int(os.getenv('SUPABASE_DB_PORT', '5432')),
            'database': os.getenv('SUPABASE_DB_NAME', os.getenv('DB_NAME', 'postgres')),
            'user': os.getenv('SUPABASE_DB_USER', os.getenv('DB_USER', 'postgres')),
            'password': os.getenv('SUPABASE_DB_PASSWORD', os.getenv('DB_PASSWORD', 'postgres')),
        }
    else:
        return {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', 'restaurant_analytics'),
            'user': os.getenv('DB_USER', 'code_executor_readonly'),  # READ-ONLY user
            'password': os.getenv('DB_PASSWORD', 'readonly_secure_password'),
        }

DB_CONFIG = get_db_config()


def get_db_connection():
    """
    Create a READ-ONLY database connection
    
    Returns:
        psycopg2 connection object
        
    Note:
        This connection uses a read-only user.
        Only SELECT queries are permitted.
    """
    return psycopg2.connect(**DB_CONFIG)


def query_db(sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Execute a SELECT query and return results as pandas DataFrame
    
    Args:
        sql: SQL SELECT query string
        params: Optional parameters for parameterized queries
        
    Returns:
        pandas DataFrame with query results
        
    Example:
        df = query_db("SELECT * FROM orders WHERE status = %s LIMIT 10", ('COMPLETED',))
        
    Note:
        Only SELECT queries are allowed. INSERT/UPDATE/DELETE will fail.
    """
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(sql, conn, params=params)
        return df
    finally:
        conn.close()


# Make connection available in global namespace for code execution
# Note: execute_sql is intentionally NOT included as this is a READ-ONLY connection
__all__ = ['get_db_connection', 'query_db', 'DB_CONFIG']


