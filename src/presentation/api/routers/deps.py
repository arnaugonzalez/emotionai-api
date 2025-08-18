"""
Router Dependencies

Shared dependencies for routers: container access and user authentication.
"""

from uuid import UUID

from fastapi import Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ....infrastructure.container import ApplicationContainer
from ....application.services.profile_service import IProfileService


security = HTTPBearer()


def get_container(request: Request) -> ApplicationContainer:
    """Get dependency injection container from app state."""
    return request.app.state.container


async def get_current_user_id(
    request: Request,
    token: HTTPAuthorizationCredentials = Depends(security),
) -> UUID:
    """Best-effort user identification.

    Priority:
      1) X-User-Id header (UUID)
      2) Authorization: Bearer <UUID>
      3) Placeholder UUID (for local/dev only)
    """
    from uuid import UUID as _UUID
    # Try header override
    hdr = request.headers.get("x-user-id") or request.headers.get("x-userid")
    if hdr:
        try:
            return _UUID(hdr)
        except Exception:
            pass
    # Try bearer token as UUID
    if token and token.credentials:
        try:
            return _UUID(token.credentials)
        except Exception:
            pass
    # Fallback placeholder for dev
    return _UUID("550e8400-e29b-41d4-a716-446655440000")


def get_profile_service(container: ApplicationContainer = Depends(get_container)) -> IProfileService:
    """Get profile service from container."""
    return container.profile_service


