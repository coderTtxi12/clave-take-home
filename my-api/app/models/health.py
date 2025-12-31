"""
Health check models with Pydantic validation
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class HealthResponse(BaseModel):
    """Health check response model"""
    
    status: str = Field(..., description="Service status", examples=["healthy"])
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Current timestamp")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-31T12:00:00.000000",
                "service": "Loan Risk API",
                "version": "1.0.0"
            }
        }


class HealthCheckDetails(BaseModel):
    """Detailed health check response"""
    
    status: str = Field(..., description="Overall service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    components: dict = Field(default_factory=dict, description="Component health status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-31T12:00:00.000000",
                "service": "Loan Risk API",
                "version": "1.0.0",
                "components": {
                    "database": "connected",
                    "redis": "connected",
                    "api": "running"
                }
            }
        }

