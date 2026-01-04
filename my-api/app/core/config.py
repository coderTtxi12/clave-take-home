"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, Union
from pathlib import Path
import json
import os


class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # API Configuration
    APP_NAME: str = "Data Analyst Agent API"
    APP_VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    
    # CORS Configuration
    ALLOWED_ORIGINS: Union[list[str], str] = ["http://localhost:3000", "http://localhost:3001"]
    
    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from string (JSON or comma-separated) to list"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # Try JSON first
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fall back to comma-separated
                return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    # Environment
    ENVIRONMENT: str = "development"  # development, production
    
    # Supabase Configuration
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    SUPABASE_DB_HOST: Optional[str] = None
    SUPABASE_DB_PORT: str = "5432"
    SUPABASE_DB_NAME: Optional[str] = None
    SUPABASE_DB_USER: Optional[str] = None
    SUPABASE_DB_PASSWORD: Optional[str] = None
    
    # PostgreSQL Configuration (for docker-compose local)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "restaurant_analytics"
    
    # Database Connection (for scripts and Alembic)
    # These will be set from environment variables or use Supabase if configured
    # The actual values are resolved at runtime via get_db_config() method
    DB_HOST: Optional[str] = None
    DB_PORT: Optional[str] = None
    DB_NAME: Optional[str] = None
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    
    def get_db_config(self) -> dict:
        """
        Get database configuration, preferring Supabase if configured.
        Returns a dict with DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
        """
        # If Supabase is configured, use it
        if self.SUPABASE_DB_HOST:
            return {
                "DB_HOST": self.SUPABASE_DB_HOST,
                "DB_PORT": self.SUPABASE_DB_PORT,
                "DB_NAME": self.SUPABASE_DB_NAME or os.getenv("DB_NAME", "postgres"),  # Supabase default is 'postgres'
                "DB_USER": self.SUPABASE_DB_USER or os.getenv("DB_USER", "postgres"),
                "DB_PASSWORD": self.SUPABASE_DB_PASSWORD or os.getenv("DB_PASSWORD", ""),
            }
        
        # Otherwise use explicit DB_* vars or fall back to POSTGRES_* or defaults
        return {
            "DB_HOST": self.DB_HOST or os.getenv("DB_HOST", "localhost"),
            "DB_PORT": self.DB_PORT or os.getenv("DB_PORT", "5433"),
            "DB_NAME": self.DB_NAME or os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "restaurant_analytics")),
            "DB_USER": self.DB_USER or os.getenv("DB_USER", os.getenv("POSTGRES_USER", "postgres")),
            "DB_PASSWORD": self.DB_PASSWORD or os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "postgres")),
        }
    
    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # Code Executor Service Configuration
    # Default to localhost for local development
    # Set CODE_EXECUTOR_URL=http://code-executor:8001 in .env if running in Docker
    CODE_EXECUTOR_URL: str = "http://localhost:8001"
    CODE_EXECUTOR_TIMEOUT: int = 30  # seconds
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None
    
    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    class Config:
        # Look for .env in project root (one level up from my-api/)
        env_file = str(BASE_DIR.parent / ".env")
        case_sensitive = True


# Global settings instance
settings = Settings()

