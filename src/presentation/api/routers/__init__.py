"""
API Routers Package

Exports all routers for the FastAPI application.
"""

from .chat import router as chat_router
from .health import router as health_router
from .auth import router as auth_router
from .records import router as records_router
from .breathing import router as breathing_router
from .usage import router as usage_router
from .data import router as data_router
from .profile import router as profile_router
from .ws import router as ws_router

__all__ = [
    "chat_router",
    "health_router",
    "auth_router",
    "records_router",
    "breathing_router",
    "usage_router",
    "data_router",
    "profile_router",
    "ws_router",
]