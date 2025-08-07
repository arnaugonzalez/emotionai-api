"""
Mock Similarity Search Service Implementation

Temporary mock implementation for development and testing.
This will be replaced with the full implementation later.
"""

from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime

from ...application.services.similarity_search_service import (
    ISimilaritySearchService, 
    SimilarityMatch
)


class MockSimilaritySearchService(ISimilaritySearchService):
    """Mock implementation of similarity search service"""
    
    async def find_similar_content(
        self,
        user_id: UUID,
        reference_tags: List[str],
        content_types: Optional[List[str]] = None,
        time_range_days: Optional[int] = None,
        min_similarity: float = 0.3,
        limit: int = 10
    ) -> List[SimilarityMatch]:
        """Return empty list for now"""
        return []
    
    async def find_similar_emotional_patterns(
        self,
        user_id: UUID,
        current_emotion: str,
        current_intensity: int,
        current_tags: List[str],
        limit: int = 5
    ) -> List[SimilarityMatch]:
        """Return empty list for now"""
        return []
    
    async def find_effective_coping_strategies(
        self,
        user_id: UUID,
        situation_tags: List[str],
        min_effectiveness: int = 3
    ) -> List[Dict[str, Any]]:
        """Return basic mock coping strategies"""
        return [
            {
                "strategy": "deep_breathing",
                "effectiveness_score": 4.2,
                "times_used": 5,
                "description": "Deep breathing exercises",
                "mock_data": True
            }
        ]
    
    async def calculate_tag_similarity(
        self,
        tags1: List[str],
        tags2: List[str]
    ) -> float:
        """Return basic similarity score"""
        if not tags1 or not tags2:
            return 0.0
        
        # Simple Jaccard similarity
        set1 = set(tags1)
        set2 = set(tags2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    async def get_tag_co_occurrence_patterns(
        self,
        user_id: UUID,
        primary_tag: str,
        time_range_days: int = 90
    ) -> Dict[str, float]:
        """Return empty dict for now"""
        return {}
    
    async def find_temporal_patterns(
        self,
        user_id: UUID,
        tags: List[str],
        time_granularity: str = "day"
    ) -> Dict[str, Any]:
        """Return mock temporal patterns"""
        return {
            "patterns_found": 0,
            "mock_data": True,
            "granularity": time_granularity
        }
    
    async def get_trending_tags_for_user(
        self,
        user_id: UUID,
        time_range_days: int = 7
    ) -> List[Tuple[str, float]]:
        """Return empty list for now"""
        return []
    
    async def cluster_user_experiences(
        self,
        user_id: UUID,
        num_clusters: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Return empty clusters for now"""
        return {}
    
    async def health_check(self) -> bool:
        """Mock service is always healthy"""
        return True