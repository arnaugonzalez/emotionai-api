"""Profile management API router"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ....application.services.profile_service import IProfileService
from ....application.dtos.profile_dtos import (
    UserProfileRequest,
    UserProfileResponse,
    TherapyContextRequest,
    TherapyContextResponse,
    ProfileStatusResponse
)
from ...dependencies import get_current_user_id, get_profile_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("/", response_model=UserProfileResponse)
async def get_user_profile(
    current_user_id: UUID = Depends(get_current_user_id),
    profile_service: IProfileService = Depends(get_profile_service)
) -> UserProfileResponse:
    """Get current user's profile"""
    try:
        profile = await profile_service.get_user_profile(current_user_id)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profile not found"
            )
        return profile
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve profile"
        )


@router.post("/", response_model=UserProfileResponse)
async def create_profile(
    profile_data: UserProfileRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    profile_service: IProfileService = Depends(get_profile_service)
) -> UserProfileResponse:
    """Create new user profile"""
    try:
        profile = await profile_service.create_or_update_profile(current_user_id, profile_data)
        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create profile"
        )


@router.put("/", response_model=UserProfileResponse)
async def update_profile(
    profile_data: UserProfileRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    profile_service: IProfileService = Depends(get_profile_service)
) -> UserProfileResponse:
    """Update existing user profile"""
    try:
        profile = await profile_service.create_or_update_profile(current_user_id, profile_data)
        return profile
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/status", response_model=ProfileStatusResponse)
async def get_profile_status(
    current_user_id: UUID = Depends(get_current_user_id),
    profile_service: IProfileService = Depends(get_profile_service)
) -> ProfileStatusResponse:
    """Get profile completion status"""
    try:
        status_response = await profile_service.get_profile_status(current_user_id)
        return status_response
    except Exception as e:
        logger.error(f"Error getting profile status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get profile status"
        )


@router.get("/therapy-context", response_model=TherapyContextResponse)
async def get_therapy_context(
    current_user_id: UUID = Depends(get_current_user_id),
    profile_service: IProfileService = Depends(get_profile_service)
) -> TherapyContextResponse:
    """Get therapy context and AI insights"""
    try:
        context = await profile_service.get_therapy_context(current_user_id)
        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Therapy context not found"
            )
        return context
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting therapy context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve therapy context"
        )


@router.put("/therapy-context", response_model=TherapyContextResponse)
async def update_therapy_context(
    context_data: TherapyContextRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    profile_service: IProfileService = Depends(get_profile_service)
) -> TherapyContextResponse:
    """Update therapy context and AI insights"""
    try:
        context = await profile_service.update_therapy_context(current_user_id, context_data)
        return context
    except Exception as e:
        logger.error(f"Error updating therapy context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update therapy context"
        )


@router.delete("/therapy-context")
async def clear_therapy_context(
    current_user_id: UUID = Depends(get_current_user_id),
    profile_service: IProfileService = Depends(get_profile_service)
) -> JSONResponse:
    """Clear therapy context and AI insights"""
    try:
        success = await profile_service.clear_therapy_context(current_user_id)
        if success:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"message": "Therapy context cleared successfully"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to clear therapy context"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing therapy context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear therapy context"
        )


@router.post("/generate-insights")
async def generate_ai_insights(
    current_user_id: UUID = Depends(get_current_user_id),
    profile_service: IProfileService = Depends(get_profile_service)
) -> JSONResponse:
    """Generate new AI insights based on user data"""
    try:
        insights = await profile_service.generate_ai_insights(current_user_id)
        if insights:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"insights": insights, "message": "AI insights generated successfully"}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate AI insights"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating AI insights: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate AI insights"
        )



