"""Profile service interface for user profile management"""

from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID

from ..dtos.profile_dtos import (
    UserProfileRequest, 
    UserProfileResponse, 
    TherapyContextRequest, 
    TherapyContextResponse,
    ProfileStatusResponse
)


class IProfileService(ABC):
    """Interface for profile management service"""
    
    @abstractmethod
    async def get_user_profile(self, user_id: UUID) -> Optional[UserProfileResponse]:
        """Get user profile by ID"""
        pass
    
    @abstractmethod
    async def create_or_update_profile(self, user_id: UUID, profile_data: UserProfileRequest) -> UserProfileResponse:
        """Create or update user profile"""
        pass
    
    @abstractmethod
    async def get_profile_status(self, user_id: UUID) -> ProfileStatusResponse:
        """Get profile completion status"""
        pass
    
    @abstractmethod
    async def get_therapy_context(self, user_id: UUID) -> Optional[TherapyContextResponse]:
        """Get therapy context and AI insights"""
        pass
    
    @abstractmethod
    async def update_therapy_context(self, user_id: UUID, context_data: TherapyContextRequest) -> TherapyContextResponse:
        """Update therapy context and AI insights"""
        pass
    
    @abstractmethod
    async def clear_therapy_context(self, user_id: UUID) -> bool:
        """Clear therapy context and AI insights"""
        pass
    
    @abstractmethod
    async def generate_ai_insights(self, user_id: UUID) -> Optional[dict]:
        """Generate new AI insights based on user data"""
        pass
