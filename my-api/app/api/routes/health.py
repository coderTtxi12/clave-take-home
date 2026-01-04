"""
Health Check API Routes

This module provides health check endpoints for monitoring and load balancing:
- GET /health: Basic health check (quick response)
- GET /health/detailed: Detailed health check with component status

These endpoints are used by:
- Load balancers to determine if the service is healthy
- Monitoring systems to track service availability
- Deployment pipelines to verify successful deployments

The basic health check returns immediately, while the detailed check
can include status of dependencies (database, Redis, etc.).
"""
from fastapi import APIRouter, status
from app.models.health import HealthResponse, HealthCheckDetails
from app.core.config import settings
from app.core.logging import get_logger
from datetime import datetime

router = APIRouter(tags=["health"])
logger = get_logger()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns the basic health status of the API service"
)
async def health_check():
    """
    Basic health check endpoint
    
    Returns:
        HealthResponse: Service health status with timestamp
    """
    logger.info("Health check endpoint called")
    
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow()
    )


@router.get(
    "/health/detailed",
    response_model=HealthCheckDetails,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Returns detailed health status including all service components"
)
async def detailed_health_check():
    """
    Detailed health check endpoint with component status
    
    Returns:
        HealthCheckDetails: Detailed service health status
    """
    logger.info("Detailed health check endpoint called")
    
    # Here you can add actual checks for database, redis, etc.
    components = {
        "api": "running",
        "database": "not_configured",  # Will be "connected" when Supabase is configured
        "redis": "not_configured",      # Will be "connected" when Redis is configured
    }
    
    return HealthCheckDetails(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        components=components
    )

