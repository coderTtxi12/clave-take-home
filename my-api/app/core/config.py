"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, Union
from pathlib import Path
import json


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
    
    # Database Configuration (Supabase)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    
    # PostgreSQL Configuration (for docker-compose)
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "restaurant_analytics"
    
    # Database Connection (for scripts and Alembic)
    DB_HOST: str = "localhost"
    DB_PORT: str = "5433"
    DB_NAME: str = "restaurant_analytics"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    
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
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

