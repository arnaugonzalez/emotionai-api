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

router = APIRouter(prefix="/profile", tags=["profile"], redirect_slashes=False) 


def _safe_model_to_dict(obj):
	"""Serialize Pydantic model (v1 or v2) or dict-like objects for logging."""
	try:
		# Pydantic v2
		return obj.model_dump()
	except AttributeError:
		try:
			# Pydantic v1
			return obj.dict()
		except Exception:
			try:
				# Already a dict or JSON-serializable
				return dict(obj)
			except Exception:
				return str(obj)


@router.get("/", response_model=UserProfileResponse)
@router.get("", response_model=UserProfileResponse)
async def get_profile(
	profile_service: IProfileService = Depends(get_profile_service),
	user_id: UUID = Depends(get_current_user_id)
):
	"""Get user profile"""
	try:
		logger.info(f"[Profile:Get] Fetching profile for user_id={user_id}")
		profile = await profile_service.get_user_profile(user_id)
		if not profile:
			logger.warning(f"[Profile:Get] Profile not found for user_id={user_id}")
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Profile not found"
			)
		logger.info(f"[Profile:Get] Profile fetched successfully for user_id={user_id}")
		return profile
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Get] Error retrieving profile for user_id={user_id}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error retrieving profile: {str(e)}"
		)


@router.post("/", response_model=UserProfileResponse)
@router.post("", response_model=UserProfileResponse)
async def create_profile(
	profile_data: UserProfileRequest,
	profile_service: IProfileService = Depends(get_profile_service),
	user_id: UUID = Depends(get_current_user_id)
):
	"""Create or update user profile"""
	payload = _safe_model_to_dict(profile_data)
	try:
		logger.info(f"[Profile:Create] Creating/updating profile for user_id={user_id}")
		logger.debug(f"[Profile:Create] Payload for user_id={user_id}: {payload}")
		profile = await profile_service.create_or_update_profile(user_id, profile_data)
		logger.info(f"[Profile:Create] Profile saved successfully for user_id={user_id}")
		return profile
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Create] Error creating profile for user_id={user_id} with payload={payload}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error creating profile: {str(e)}"
		)


@router.put("/", response_model=UserProfileResponse)
@router.put("", response_model=UserProfileResponse)
async def update_profile(
	profile_data: UserProfileRequest,
	current_user_id: UUID = Depends(get_current_user_id),
	profile_service: IProfileService = Depends(get_profile_service)
) -> UserProfileResponse:
	"""Update existing user profile"""
	payload = _safe_model_to_dict(profile_data)
	try:
		logger.info(f"[Profile:Update] Updating profile for user_id={current_user_id}")
		logger.debug(f"[Profile:Update] Payload for user_id={current_user_id}: {payload}")
		profile = await profile_service.create_or_update_profile(current_user_id, profile_data)
		logger.info(f"[Profile:Update] Profile updated successfully for user_id={current_user_id}")
		return profile
	except ValueError as e:
		logger.warning(f"[Profile:Update] Validation error for user_id={current_user_id}: {e}")
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail=str(e)
		)
	except Exception as e:
		logger.exception(f"[Profile:Update] Error updating profile for user_id={current_user_id} with payload={payload}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="Failed to update profile"
		)


@router.get("/status", response_model=ProfileStatusResponse)
async def get_profile_status(
	profile_service: IProfileService = Depends(get_profile_service),
	user_id: UUID = Depends(get_current_user_id)
):
	"""Get profile completion status"""
	try:
		logger.info(f"[Profile:Status] Getting profile status for user_id={user_id}")
		status_response = await profile_service.get_profile_status(user_id)
		logger.info(f"[Profile:Status] Status computed for user_id={user_id}: {status_response.profile_completeness}")
		return status_response
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Status] Error getting status for user_id={user_id}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error getting profile status: {str(e)}"
		)


@router.get("/therapy-context", response_model=TherapyContextResponse)
async def get_therapy_context(
	profile_service: IProfileService = Depends(get_profile_service),
	user_id: UUID = Depends(get_current_user_id)
):
	"""Get therapy context and AI insights"""
	try:
		logger.info(f"[Profile:Context:Get] Fetching therapy context for user_id={user_id}")
		context = await profile_service.get_therapy_context(user_id)
		if not context:
			logger.warning(f"[Profile:Context:Get] Context not found for user_id={user_id}")
			raise HTTPException(
				status_code=status.HTTP_404_NOT_FOUND,
				detail="Therapy context not found"
			)
		logger.info(f"[Profile:Context:Get] Context fetched for user_id={user_id}")
		return context
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Context:Get] Error retrieving context for user_id={user_id}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error retrieving therapy context: {str(e)}"
		)


@router.put("/therapy-context", response_model=TherapyContextResponse)
async def update_therapy_context(
	context_data: TherapyContextRequest,
	profile_service: IProfileService = Depends(get_profile_service),
	user_id: UUID = Depends(get_current_user_id)
):
	"""Update therapy context and AI insights"""
	payload = _safe_model_to_dict(context_data)
	try:
		logger.info(f"[Profile:Context:Update] Updating therapy context for user_id={user_id}")
		logger.debug(f"[Profile:Context:Update] Payload for user_id={user_id}: {payload}")
		context = await profile_service.update_therapy_context(user_id, context_data)
		logger.info(f"[Profile:Context:Update] Context updated for user_id={user_id}")
		return context
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Context:Update] Error updating context for user_id={user_id} with payload={payload}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error updating therapy context: {str(e)}"
		)


@router.delete("/therapy-context")
async def clear_therapy_context(
	profile_service: IProfileService = Depends(get_profile_service),
	user_id: UUID = Depends(get_current_user_id)
):
	"""Clear therapy context and AI insights"""
	try:
		logger.info(f"[Profile:Context:Clear] Clearing therapy context for user_id={user_id}")
		success = await profile_service.clear_therapy_context(user_id)
		if success:
			logger.info(f"[Profile:Context:Clear] Cleared therapy context for user_id={user_id}")
			return {"message": "Therapy context cleared successfully"}
		else:
			logger.error(f"[Profile:Context:Clear] Failed to clear therapy context for user_id={user_id}")
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="Failed to clear therapy context"
			)
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Context:Clear] Error clearing context for user_id={user_id}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error clearing therapy context: {str(e)}"
		)


@router.post("/generate-insights")
async def generate_ai_insights(
	current_user_id: UUID = Depends(get_current_user_id),
	profile_service: IProfileService = Depends(get_profile_service)
) -> JSONResponse:
	"""Generate new AI insights based on user data"""
	try:
		logger.info(f"[Profile:Insights] Generating AI insights for user_id={current_user_id}")
		insights = await profile_service.generate_ai_insights(current_user_id)
		if insights:
			logger.info(f"[Profile:Insights] Generated AI insights for user_id={current_user_id}")
			return JSONResponse(
				status_code=status.HTTP_200_OK,
				content={"insights": "AI insights generated successfully"}
			)
		else:
			logger.error(f"[Profile:Insights] Failed to generate AI insights for user_id={current_user_id}")
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="Failed to generate AI insights"
			)
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Insights] Error generating AI insights for user_id={current_user_id}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="Failed to generate AI insights"
		)


@router.get("/agent-personality")
async def get_agent_personality(
	profile_service: IProfileService = Depends(get_profile_service),
	user_id: UUID = Depends(get_current_user_id)
):
	"""Get AI agent personality settings and context"""
	try:
		logger.info(f"[Profile:Personality:Get] Fetching agent personality for user_id={user_id}")
		# This would need to be implemented in the profile service
		# For now, return a placeholder
		return {
			"message": "Agent personality endpoint - to be implemented",
			"user_id": user_id
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Personality:Update] Error retrieving agent personality for user_id={user_id}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error retrieving agent personality: {str(e)}"
		)


@router.put("/agent-personality")
async def update_agent_personality(
	personality_data: dict,
	profile_service: IProfileService = Depends(get_profile_service),
	user_id: UUID = Depends(get_current_user_id)
):
	"""Update AI agent personality settings and context"""
	try:
		logger.info(f"[Profile:Personality:Update] Updating agent personality for user_id={user_id}")
		logger.debug(f"[Profile:Personality:Update] Payload for user_id={user_id}: {personality_data}")
		# This would need to be implemented in the profile service
		# For now, return a placeholder
		return {
			"message": "Agent personality update endpoint - to be implemented",
			"user_id": user_id,
			"data": personality_data
		}
	except HTTPException:
		raise
	except Exception as e:
		logger.exception(f"[Profile:Personality:Update] Error updating agent personality for user_id={user_id}: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Error updating agent personality: {str(e)}"
		)



