"""
Mock User Knowledge Service Implementation

Temporary mock implementation for development and testing.
This will be replaced with the full implementation later.
"""

from typing import Dict, Any, Optional, List
from uuid import UUID

from ...application.services.user_knowledge_service import (
    IUserKnowledgeService, 
    UserKnowledgeProfile, 
    UserInsight
)


class MockUserKnowledgeService(IUserKnowledgeService):
    """Mock implementation of user knowledge service"""
    
    async def update_user_profile_with_tags(
        self,
        user_id: UUID,
        data_type: str,
        tags: List[str],
        confidence: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Mock update - just log the operation"""
        pass
    
    async def get_user_profile(self, user_id: UUID) -> Optional[UserKnowledgeProfile]:
        """Return mock profile"""
        return None
    
    async def get_personalization_context(
        self, 
        user_id: UUID, 
        context_type: str = "chat"
    ) -> Dict[str, Any]:
        """Return basic mock context"""
        return {
            "user_id": str(user_id),
            "context_type": context_type,
            "profile_completeness": 0.3,
            "mock_service": True
        }
    
    async def find_similar_past_experiences(
        self,
        user_id: UUID,
        current_tags: List[str],
        data_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Return empty list for now"""
        return []
    
    async def generate_user_insights(self, user_id: UUID) -> List[UserInsight]:
        """Return empty list for now"""
        return []
    
    async def get_wellness_recommendations(
        self,
        user_id: UUID,
        current_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Return basic wellness recommendations"""
        return [
            {
                "type": "breathing_exercise",
                "title": "Try Deep Breathing",
                "description": "Take 5 deep breaths to help with relaxation",
                "confidence": 0.7
            }
        ]
    
    async def analyze_behavioral_patterns(
        self, 
        user_id: UUID,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Return mock behavioral analysis"""
        return {
            "patterns_detected": 0,
            "mock_analysis": True,
            "time_period": time_period_days
        }
    
    async def get_user_tag_trends(
        self,
        user_id: UUID,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Return mock tag trends"""
        return {
            "trending_tags": [],
            "mock_data": True
        }
    
    async def health_check(self) -> bool:
        """Mock service is always healthy"""
        return True