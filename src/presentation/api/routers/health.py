"""
Health Check Router

Provides health check endpoints for monitoring and load balancers.
"""

import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ....infrastructure.container import ApplicationContainer
from ....infrastructure.database.models import UserModel
from sqlalchemy import select
from ....infrastructure.config.settings import settings

router = APIRouter(redirect_slashes=False)


def get_container(request: Request) -> ApplicationContainer:
    """Get dependency injection container from app state"""
    return request.app.state.container


@router.get("/", summary="Basic health check")
async def health_check(request: Request, container: ApplicationContainer = Depends(get_container)):
    """Basic health check endpoint with dev placeholder ensure."""
    if settings.environment != "production":
        from uuid import UUID
        placeholder_id = UUID("550e8400-e29b-41d4-a716-446655440000")
        db = container.database
        async with db.get_session() as session:
            res = await session.execute(select(UserModel).where(UserModel.id == placeholder_id))
            user = res.scalar_one_or_none()
            if user is None:
                user = UserModel(
                    id=placeholder_id,
                    email="dev+placeholder@example.com",
                    hashed_password="dev",
                    first_name="Dev",
                    last_name="User",
                    is_active=True,
                    is_verified=False,
                )
                session.add(user)
                await session.commit()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
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
        "timestamp": datetime.utcnow().isoformat(),
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
                "timestamp": datetime.utcnow().isoformat(),
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
            "timestamp": datetime.utcnow().isoformat()
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
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time()
    } 