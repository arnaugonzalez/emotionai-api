"""
Dependency injection functions for FastAPI endpoints

This module provides dependency functions that can be used with FastAPI's Depends()
to inject services and other dependencies into endpoint handlers.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..infrastructure.container import get_container
from ..application.services.profile_service import IProfileService
from ..application.services.agent_service import IAgentService
from ..application.services.event_bus import IEventBus
from ..application.services.tagging_service import ITaggingService
from ..application.services.user_knowledge_service import IUserKnowledgeService
from ..application.services.similarity_search_service import ISimilaritySearchService

logger = logging.getLogger(__name__)

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)

async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UUID:
    """Extract current user ID from JWT token"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    try:
        # TODO: Implement proper JWT token validation
        # For now, return a mock user ID for development
        # In production, this should decode and validate the JWT token
        from uuid import uuid4
        mock_user_id = UUID('550e8400e29b41d4a716446655440000')
        logger.warning(f"Using mock test@example.com ID: {mock_user_id} - JWT validation not implemented")
        return mock_user_id
        
    except Exception as e:
        logger.error(f"Error extracting user ID from token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

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
