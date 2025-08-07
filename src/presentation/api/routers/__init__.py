"""
API Routers Package

Exports all routers for the FastAPI application.
"""

from .chat import router as chat_router
from .health import router as health_router
from .auth import router as auth_router
from .data import router as data_router

__all__ = ["chat_router", "health_router", "auth_router", "data_router"] 