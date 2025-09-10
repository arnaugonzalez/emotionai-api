"""
Router Dependencies

Shared dependencies for routers: container access and user authentication.
"""

from uuid import UUID

from fastapi import Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ....infrastructure.container import ApplicationContainer
from ....application.services.profile_service import IProfileService
from ...dependencies import get_current_user_id as _jwt_get_current_user_id


security = HTTPBearer()


def get_container(request: Request) -> ApplicationContainer:
    """Get dependency injection container from app state."""
    return request.app.state.container


async def get_current_user_id(
    token: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """JWT-based user identification using centralized dependency."""
    return await _jwt_get_current_user_id(token)


def get_profile_service(container: ApplicationContainer = Depends(get_container)) -> IProfileService:
    """Get profile service from container."""
    return container.profile_service


