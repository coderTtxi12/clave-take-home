"""
Logging Configuration

This module provides centralized logging configuration for the application.
It sets up structured logging with:
- Configurable log levels (from settings)
- Console output with formatted timestamps
- Consistent log format across all modules

The logger is configured once at module import and reused throughout
the application via the get_logger() function.
"""
import logging
import sys
from app.core.config import settings


def setup_logging():
    """
    Configure application logging with console handler.
    
    Sets up a logger with:
    - Log level from settings (default: INFO)
    - Console output to stdout
    - Formatted timestamps and messages
    - No propagation to root logger (prevents duplicate logs)
    
    Returns:
        Configured logger instance
    """
    
    # Create logger
    logger = logging.getLogger("loan_risk_api")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Create formatter
    formatter = logging.Formatter(
        settings.LOG_FORMAT,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Prevent propagation to root logger
    logger.propagate = False
    
    return logger


# Global logger instance
logger = setup_logging()


def get_logger():
    """
    Get the global application logger instance.
    
    This function provides access to the configured logger from any module.
    The logger is initialized once at module import time.
    
    Returns:
        Logger instance configured for the application
    """
    return logger

