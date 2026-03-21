"""
Router Dependencies

Shared dependencies for routers: container access and service helpers.
"""

from fastapi import Request, Depends

from ....infrastructure.container import ApplicationContainer
from ....application.services.profile_service import IProfileService


def get_container(request: Request) -> ApplicationContainer:
    """Get dependency injection container from app state."""
    return request.app.state.container


def get_profile_service(container: ApplicationContainer = Depends(get_container)) -> IProfileService:
    """Get profile service from container."""
    return container.profile_service
