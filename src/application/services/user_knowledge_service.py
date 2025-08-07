"""
User Knowledge Service Interface

This service builds and maintains intelligent user profiles based on tagged data.
It provides personalized insights and context for agent interactions.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime


class UserInsight:
    """Represents an insight about a user"""
    
    def __init__(
        self,
        category: str,
        description: str,
        confidence: float,
        supporting_data: List[str],
        created_at: datetime = None
    ):
        self.category = category  # e.g., "emotional_patterns", "coping_preferences", "behavioral_trends"
        self.description = description
        self.confidence = confidence
        self.supporting_data = supporting_data
        self.created_at = created_at or datetime.utcnow()


class UserKnowledgeProfile:
    """Complete user knowledge profile"""
    
    def __init__(
        self,
        user_id: UUID,
        frequent_tags: Dict[str, int],
        tag_categories: Dict[str, List[str]],
        insights: List[UserInsight],
        behavioral_patterns: Dict[str, Any],
        preferences: Dict[str, Any],
        last_updated: datetime = None
    ):
        self.user_id = user_id
        self.frequent_tags = frequent_tags
        self.tag_categories = tag_categories
        self.insights = insights
        self.behavioral_patterns = behavioral_patterns
        self.preferences = preferences
        self.last_updated = last_updated or datetime.utcnow()


class IUserKnowledgeService(ABC):
    """Interface for user knowledge management operations"""
    
    @abstractmethod
    async def update_user_profile_with_tags(
        self,
        user_id: UUID,
        data_type: str,  # 'message', 'emotional_record', 'breathing_session'
        tags: List[str],
        confidence: float,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update user profile with new tagged data
        
        Args:
            user_id: User identifier
            data_type: Type of data that was tagged
            tags: Extracted tags
            confidence: Confidence in tag extraction
            additional_context: Any additional context data
        """
        pass
    
    @abstractmethod
    async def get_user_profile(self, user_id: UUID) -> Optional[UserKnowledgeProfile]:
        """
        Get complete user knowledge profile
        
        Args:
            user_id: User identifier
            
        Returns:
            UserKnowledgeProfile if exists, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_personalization_context(
        self, 
        user_id: UUID, 
        context_type: str = "chat"
    ) -> Dict[str, Any]:
        """
        Get personalization context for agent interactions
        
        Args:
            user_id: User identifier
            context_type: Type of context needed ('chat', 'recommendations', etc.)
            
        Returns:
            Dictionary containing personalization context
        """
        pass
    
    @abstractmethod
    async def find_similar_past_experiences(
        self,
        user_id: UUID,
        current_tags: List[str],
        data_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar past experiences based on tag similarity
        
        Args:
            user_id: User identifier
            current_tags: Tags to find similarities for
            data_types: Types of data to search in (optional)
            limit: Maximum number of results
            
        Returns:
            List of similar past experiences with similarity scores
        """
        pass
    
    @abstractmethod
    async def generate_user_insights(self, user_id: UUID) -> List[UserInsight]:
        """
        Generate new insights about the user based on their data
        
        Args:
            user_id: User identifier
            
        Returns:
            List of newly generated insights
        """
        pass
    
    @abstractmethod
    async def get_wellness_recommendations(
        self,
        user_id: UUID,
        current_context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get personalized wellness recommendations
        
        Args:
            user_id: User identifier
            current_context: Current user context
            
        Returns:
            List of personalized recommendations
        """
        pass
    
    @abstractmethod
    async def analyze_behavioral_patterns(
        self, 
        user_id: UUID,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze user's behavioral patterns over time
        
        Args:
            user_id: User identifier
            time_period_days: Time period to analyze
            
        Returns:
            Dictionary containing behavioral pattern analysis
        """
        pass
    
    @abstractmethod
    async def get_user_tag_trends(
        self,
        user_id: UUID,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """
        Get user's tag usage trends over time
        
        Args:
            user_id: User identifier
            time_period_days: Time period to analyze
            
        Returns:
            Dictionary containing tag trends and patterns
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if user knowledge service is healthy"""
        pass