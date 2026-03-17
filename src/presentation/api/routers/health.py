"""
Health Check Router

Provides health check endpoints for monitoring and load balancers.
"""

import time
from datetime import datetime, timezone
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ....infrastructure.container import ApplicationContainer
from ....infrastructure.config.settings import settings
from .deps import get_container

router = APIRouter(redirect_slashes=False)


@router.get("/", summary="Basic health check")
async def health_check(request: Request, container: ApplicationContainer = Depends(get_container)):
    """Basic health check endpoint — read-only, no side effects."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.version,
        "environment": settings.environment
    }


@router.get("/detailed", summary="Detailed health check")
async def detailed_health_check(
    request: Request,
    container: ApplicationContainer = Depends(get_container)
):
    """Detailed health check with component status"""
    
    start_time = time.time()
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.version,
        "environment": settings.environment,
        "components": {}
    }
    
    try:
        # Use the container's built-in health check
        container_health = await container.health_check()
        health_data.update(container_health)
        
        # Add performance metrics
        response_time = time.time() - start_time
        health_data["response_time_ms"] = round(response_time * 1000, 2)
        
        # Return appropriate HTTP status
        status_code = 200 if health_data["status"] == "healthy" else 503
        
        return JSONResponse(
            status_code=status_code,
            content=health_data
        )
        
    except Exception as e:
        # If health check itself fails
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": "Health check failed",
                "details": str(e)
            }
        )


@router.get("/ready", summary="Readiness check")
async def readiness_check(
    request: Request,
    container: ApplicationContainer = Depends(get_container)
):
    """Readiness check for Kubernetes or other orchestrators"""
    
    try:
        # Check critical components only
        db_ready = await container.database.health_check()
        
        if not db_ready:
            return JSONResponse(
                status_code=503,
                content={
                    "ready": False,
                    "reason": "Database not ready"
                }
            )
        
        return {
            "ready": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "ready": False,
                "reason": str(e)
            }
        )


@router.get("/live", summary="Liveness check")
async def liveness_check():
    """Liveness check for Kubernetes or other orchestrators"""
    
    # Simple check that the application is running
    return {
        "alive": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": time.time()
    } 