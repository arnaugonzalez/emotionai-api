"""
Usage Router

Provides endpoints related to usage limits and token consumption analytics.
"""

from datetime import datetime
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ....infrastructure.container import ApplicationContainer
from .deps import get_current_user_id, get_container

logger = logging.getLogger(__name__)

router = APIRouter(redirect_slashes=False)


@router.get("/user/limitations", summary="Get monthly token usage and limits")
async def get_user_limitations(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    """Return monthly token usage and limit for current user"""
    try:
        now = datetime.now()
        monthly_tokens = await container.get_monthly_usage_use_case.execute(user_id, now.year, now.month)
        monthly_limit = 250_000
        can_make_request = monthly_tokens < monthly_limit
        remaining = max(0, monthly_limit - monthly_tokens)
        usage_pct = round((monthly_tokens / monthly_limit) * 100, 2)

        return {
            "period": f"{now.year}-{now.month:02d}",
            "monthly_token_limit": monthly_limit,
            "monthly_tokens_used": monthly_tokens,
            "remaining_tokens": remaining,
            "usage_percentage": usage_pct,
            "can_make_request": can_make_request,
            "limit_message": None if can_make_request else "Monthly token limit reached",
            "limit_reset_time": datetime(now.year, now.month, 1).isoformat()
        }
    except Exception as e:
        logger.error(f"Error in get_user_limitations: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve user limitations")


