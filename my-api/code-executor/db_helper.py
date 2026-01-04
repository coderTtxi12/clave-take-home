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
# Always uses local PostgreSQL container (service name: 'postgres')
# Uses READ-ONLY user: code_executor_readonly
def get_db_config():
    """Get database configuration for local PostgreSQL container"""
    return {
        'host': os.getenv('DB_HOST', 'postgres'),  # Docker service name
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'restaurant_analytics'),
        'user': os.getenv('DB_USER', 'code_executor_readonly'),  # READ-ONLY user
        'password': os.getenv('DB_PASSWORD', 'readonly_secure_password'),
    }

DB_CONFIG = get_db_config()


def get_db_connection():
    """
    Create a READ-ONLY database connection to local PostgreSQL container
    
    Returns:
        psycopg2 connection object
        
    Note:
        This connection uses a read-only user.
        Only SELECT queries are permitted.
        Connects to PostgreSQL container using Docker service name 'postgres'.
    """
    config = DB_CONFIG.copy()
    # Docker handles service name resolution internally, no need for hostname resolution
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


