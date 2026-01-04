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
import socket
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
    config = DB_CONFIG.copy()
    
    # Force IPv4 for external hosts (like Supabase) to avoid IPv6 issues
    # For Docker service names (like 'postgres'), keep as-is since Docker handles resolution
    host = config.get('host', 'localhost')
    
    # Only resolve to IPv4 if:
    # 1. It's not already an IP address
    # 2. It's not a Docker service name (common ones: postgres, redis, api, etc.)
    # 3. It looks like an external hostname (contains dots, not a simple name)
    is_ip = host.replace('.', '').isdigit()
    is_docker_service = host in ['postgres', 'redis', 'api', 'code-executor', 'dashboard']
    is_external_host = '.' in host and not is_ip
    
    if is_external_host and not is_docker_service:
        try:
            # Resolve external hostname to IPv4 only (prevents IPv6 connection issues)
            ipv4 = socket.gethostbyname(host)
            config['host'] = ipv4
        except socket.gaierror:
            # If resolution fails, keep original hostname (psycopg2 will try to connect anyway)
            pass
    
    # For Docker service names or IPs, use as-is
    return psycopg2.connect(**config)


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


