"""
Similarity Search Service Interface

This service provides intelligent content discovery based on semantic tag similarity.
It enables finding related past experiences and content for personalized responses.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime


class SimilarityMatch:
    """Represents a similarity match result"""
    
    def __init__(
        self,
        item_id: UUID,
        item_type: str,  # 'message', 'emotional_record', 'breathing_session'
        similarity_score: float,
        matching_tags: List[str],
        content_summary: str,
        created_at: datetime,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        self.item_id = item_id
        self.item_type = item_type
        self.similarity_score = similarity_score
        self.matching_tags = matching_tags
        self.content_summary = content_summary
        self.created_at = created_at
        self.additional_data = additional_data or {}


class ISimilaritySearchService(ABC):
    """Interface for tag-based similarity search operations"""
    
    @abstractmethod
    async def find_similar_content(
        self,
        user_id: UUID,
        reference_tags: List[str],
        content_types: Optional[List[str]] = None,
        time_range_days: Optional[int] = None,
        min_similarity: float = 0.3,
        limit: int = 10
    ) -> List[SimilarityMatch]:
        """
        Find content similar to given tags for a specific user
        
        Args:
            user_id: User identifier
            reference_tags: Tags to find similar content for
            content_types: Types of content to search ('message', 'emotional_record', etc.)
            time_range_days: Limit search to recent days (optional)
            min_similarity: Minimum similarity score threshold
            limit: Maximum number of results
            
        Returns:
            List of SimilarityMatch objects ordered by similarity score
        """
        pass
    
    @abstractmethod
    async def find_similar_emotional_patterns(
        self,
        user_id: UUID,
        current_emotion: str,
        current_intensity: int,
        current_tags: List[str],
        limit: int = 5
    ) -> List[SimilarityMatch]:
        """
        Find similar emotional experiences from the past
        
        Args:
            user_id: User identifier
            current_emotion: Current emotion
            current_intensity: Current intensity level
            current_tags: Current situation tags
            limit: Maximum number of results
            
        Returns:
            List of similar emotional experiences
        """
        pass
    
    @abstractmethod
    async def find_effective_coping_strategies(
        self,
        user_id: UUID,
        situation_tags: List[str],
        min_effectiveness: int = 3  # 1-5 scale
    ) -> List[Dict[str, Any]]:
        """
        Find coping strategies that worked well in similar situations
        
        Args:
            user_id: User identifier
            situation_tags: Tags describing current situation
            min_effectiveness: Minimum effectiveness rating
            
        Returns:
            List of effective coping strategies with context
        """
        pass
    
    @abstractmethod
    async def calculate_tag_similarity(
        self,
        tags1: List[str],
        tags2: List[str]
    ) -> float:
        """
        Calculate similarity score between two tag sets
        
        Args:
            tags1: First set of tags
            tags2: Second set of tags
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        pass
    
    @abstractmethod
    async def get_tag_co_occurrence_patterns(
        self,
        user_id: UUID,
        primary_tag: str,
        time_range_days: int = 90
    ) -> Dict[str, float]:
        """
        Get tags that frequently occur with a primary tag
        
        Args:
            user_id: User identifier
            primary_tag: Tag to find co-occurrences for
            time_range_days: Time period to analyze
            
        Returns:
            Dictionary mapping co-occurring tags to their frequency scores
        """
        pass
    
    @abstractmethod
    async def find_temporal_patterns(
        self,
        user_id: UUID,
        tags: List[str],
        time_granularity: str = "day"  # 'hour', 'day', 'week'
    ) -> Dict[str, Any]:
        """
        Find temporal patterns in tag usage
        
        Args:
            user_id: User identifier
            tags: Tags to analyze patterns for
            time_granularity: Time granularity for pattern analysis
            
        Returns:
            Dictionary containing temporal pattern analysis
        """
        pass
    
    @abstractmethod
    async def get_trending_tags_for_user(
        self,
        user_id: UUID,
        time_range_days: int = 7
    ) -> List[Tuple[str, float]]:
        """
        Get trending tags for a user (increasing in frequency)
        
        Args:
            user_id: User identifier
            time_range_days: Time period to analyze for trends
            
        Returns:
            List of (tag, trend_score) tuples ordered by trend strength
        """
        pass
    
    @abstractmethod
    async def cluster_user_experiences(
        self,
        user_id: UUID,
        num_clusters: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Cluster user experiences based on tag similarity
        
        Args:
            user_id: User identifier
            num_clusters: Number of clusters to create
            
        Returns:
            Dictionary mapping cluster names to experience lists
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if similarity search service is healthy"""
        pass