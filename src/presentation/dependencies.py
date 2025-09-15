"""
Dependency injection functions for FastAPI endpoints

This module provides dependency functions that can be used with FastAPI's Depends()
to inject services and other dependencies into endpoint handlers.
"""

import logging
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from ..infrastructure.config.settings import settings
from ..infrastructure.container import get_container
from ..application.services.profile_service import IProfileService
from ..application.services.agent_service import IAgentService
from ..application.services.event_bus import IEventBus
from ..application.services.tagging_service import ITaggingService
from ..application.services.user_knowledge_service import IUserKnowledgeService
from ..application.services.similarity_search_service import ISimilaritySearchService

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=True)

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UUID:
    """Extracts and validates the user ID from JWT access token in the Authorization header"""
    try:
        data = jwt.decode(credentials.credentials, settings.secret_key, algorithms=[settings.algorithm])
        token_type = data.get("typ")
        subject = data.get("sub")
        issuer = data.get("iss")
        if token_type != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
        if not subject:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing subject in token")
        if issuer and issuer != "emotionai-api":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token issuer")
        return UUID(subject)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired authentication token")

async def get_profile_service() -> IProfileService:
    """Get profile service instance"""
    try:
        container = await get_container()
        return container.profile_service
    except Exception as e:
        logger.error(f"Error getting profile service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service unavailable"
        )

async def get_agent_service() -> IAgentService:
    """Get agent service instance"""
    try:
        container = await get_container()
        return container.agent_service
    except Exception as e:
        logger.error(f"Error getting agent service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service unavailable"
        )

async def get_event_bus() -> IEventBus:
    """Get event bus instance"""
    try:
        container = await get_container()
        return container.event_bus
    except Exception as e:
        logger.error(f"Error getting event bus: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service unavailable"
        )

async def get_tagging_service() -> ITaggingService:
    """Get tagging service instance"""
    try:
        container = await get_container()
        return container.tagging_service
    except Exception as e:
        logger.error(f"Error getting tagging service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service unavailable"
        )

async def get_user_knowledge_service() -> IUserKnowledgeService:
    """Get user knowledge service instance"""
    try:
        container = await get_container()
        return container.user_knowledge_service
    except Exception as e:
        logger.error(f"Error getting user knowledge service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service unavailable"
        )

async def get_similarity_search_service() -> ISimilaritySearchService:
    """Get similarity search service instance"""
    try:
        container = await get_container()
        return container.similarity_search_service
    except Exception as e:
        logger.error(f"Error getting similarity search service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Service unavailable"
        )
