"""
EmotionAI API - Clean Architecture Entry Point

FastAPI application with clean architecture principles.
"""

import asyncio
import logging
import uvicorn
from contextlib import asynccontextmanager
from typing import Dict, Any
from src import __version__ as app_version
from fastapi import FastAPI, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.infrastructure.config.settings import settings
from src.infrastructure.container import ApplicationContainer, initialize_container, shutdown_container
from src.presentation.api.routers import (
    chat_router,
    suggestions_router,
    health_router,
    auth_router,
    records_router,
    breathing_router,
    usage_router,
    data_router,
    profile_router,
    ws_router,
    dev_seed_router,
)
from src.presentation.api.middleware import (
    LoggingMiddleware, 
    ErrorHandlingMiddleware,
    RateLimitingMiddleware
)
from src.application.exceptions import ApplicationException
from src.presentation.api.routers.deps import get_current_user_id

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    
    # Startup
    logger.info("Starting EmotionAI API with Clean Architecture...")
    
    try:
        # Initialize container with settings
        container = await initialize_container(settings.__dict__)
        
        # Store container in app state
        app.state.container = container
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down EmotionAI API...")
        
        try:
            await shutdown_container()
            logger.info("Application shutdown completed successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


def create_application() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title=settings.app_name,
        description="Enterprise-grade EmotionAI API with Clean Architecture",
        version=app_version,
        debug=settings.debug,
        lifespan=lifespan,
        redirect_slashes=False,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )
    
    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Configure trusted hosts
    if not settings.is_development:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.trusted_hosts,
        )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    
    if settings.rate_limit_requests > 0:
        app.add_middleware(
            RateLimitingMiddleware,
            requests_per_minute=settings.rate_limit_requests
        )
    
    # Add exception handlers
    add_exception_handlers(app)
    
    # Include routers with /v1/api prefix for main API endpoints
    app.include_router(health_router, prefix="/health", tags=["Health"])
    app.include_router(auth_router, prefix="/v1/api/auth", tags=["Authentication"])
    # Mobile logs (JWT required)
    from src.presentation.api.routers.mobile_logs import router as mobile_logs_router
    app.include_router(mobile_logs_router, prefix="/v1/api", tags=["Mobile Logs"], dependencies=[Depends(get_current_user_id)])
    # Protected routers
    app.include_router(chat_router, prefix="/v1/api", tags=["Chat"], dependencies=[Depends(get_current_user_id)])
    app.include_router(records_router, prefix="/v1/api", tags=["Records"], dependencies=[Depends(get_current_user_id)])
    app.include_router(breathing_router, prefix="/v1/api", tags=["Breathing"], dependencies=[Depends(get_current_user_id)])
    app.include_router(usage_router, prefix="/v1/api", tags=["Usage"], dependencies=[Depends(get_current_user_id)])
    app.include_router(suggestions_router, prefix="/v1/api", tags=["Suggestions"], dependencies=[Depends(get_current_user_id)])
    app.include_router(data_router, prefix="/v1/api", tags=["Data"], dependencies=[Depends(get_current_user_id)])
    app.include_router(profile_router, prefix="/v1/api", tags=["Profile"], dependencies=[Depends(get_current_user_id)])
    # For websockets, handle token manually inside route and mount at /ws/*
    app.include_router(ws_router, prefix="", tags=["Realtime"])
    # Dev-only seed endpoints
    if settings.is_development:
        app.include_router(dev_seed_router, prefix="/v1/api", tags=["Dev Seed"])
    
    return app


def add_exception_handlers(app: FastAPI):
    """Add custom exception handlers"""
    
    @app.exception_handler(ApplicationException)
    async def application_exception_handler(request: Request, exc: ApplicationException):
        """Handle application layer exceptions"""
        logger.error(f"Application error: {exc.message}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "application_error",
                "message": exc.message,
                "details": exc.details
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle request validation errors"""
        logger.error(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle general exceptions"""
        logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": "An unexpected error occurred"
            }
        )


# Create the FastAPI application
app = create_application()
if __name__ == "__main__":
    """Run the application with uvicorn"""
    
    # Configure uvicorn settings
    uvicorn_config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": 8000,
        "reload": settings.is_development,
        "log_level": settings.log_level.lower(),
        "access_log": settings.is_development,
    }
    
    if settings.is_production:
        uvicorn_config.update({
            "workers": 4,
            "loop": "uvloop",
            "http": "httptools",
        })
    
    logger.info(f"Starting EmotionAI API on {uvicorn_config['host']}:{uvicorn_config['port']}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    uvicorn.run(**uvicorn_config) 