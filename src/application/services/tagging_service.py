"""
Intelligent Tagging Service Interface

This service extracts semantic tags from user content using LLM analysis.
It replaces the crisis detection system with intelligent content understanding.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID


class TagExtractionResult:
    """Result from tag extraction operation"""
    
    def __init__(
        self, 
        tags: List[str], 
        confidence: float, 
        categories: Optional[Dict[str, List[str]]] = None,
        insights: Optional[List[str]] = None
    ):
        self.tags = tags
        self.confidence = confidence
        self.categories = categories or {}  # e.g., {"emotional": ["anxious"], "behavioral": ["seeking_help"]}
        self.insights = insights or []  # LLM-generated insights about the content


class ITaggingService(ABC):
    """Interface for intelligent content tagging operations"""
    
    @abstractmethod
    async def extract_tags_from_message(
        self, 
        content: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> TagExtractionResult:
        """
        Extract semantic tags from a chat message
        
        Args:
            content: The message content to analyze
            user_context: Optional context about the user for better tagging
            
        Returns:
            TagExtractionResult with extracted tags and insights
        """
        pass
    
    @abstractmethod
    async def extract_tags_from_emotional_record(
        self,
        emotion: str,
        intensity: int,
        triggers: Optional[List[str]] = None,
        notes: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> TagExtractionResult:
        """
        Extract semantic tags from an emotional record
        
        Args:
            emotion: The primary emotion
            intensity: Emotion intensity (1-10)
            triggers: List of triggers
            notes: Additional notes
            user_context: Optional user context
            
        Returns:
            TagExtractionResult with extracted tags and insights
        """
        pass
    
    @abstractmethod
    async def extract_tags_from_breathing_session(
        self,
        pattern_name: str,
        duration_minutes: int,
        effectiveness_rating: Optional[int] = None,
        notes: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> TagExtractionResult:
        """
        Extract semantic tags from a breathing session
        
        Args:
            pattern_name: Name of breathing pattern used
            duration_minutes: Session duration
            effectiveness_rating: User rating (1-5)
            notes: Additional notes
            user_context: Optional user context
            
        Returns:
            TagExtractionResult with extracted tags and insights
        """
        pass
    
    @abstractmethod
    async def categorize_tags(self, tags: List[str]) -> Dict[str, List[str]]:
        """
        Categorize tags into semantic groups
        
        Args:
            tags: List of tags to categorize
            
        Returns:
            Dictionary mapping categories to tag lists
        """
        pass
    
    @abstractmethod
    async def find_similar_tags(
        self, 
        tag: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find semantically similar tags
        
        Args:
            tag: Tag to find similarities for
            limit: Maximum number of similar tags to return
            
        Returns:
            List of similar tags with similarity scores
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if tagging service is healthy"""
        pass