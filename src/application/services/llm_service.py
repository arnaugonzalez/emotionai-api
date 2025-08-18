"""
LLM Service Interface

Abstract interface for language model services that provide therapeutic responses.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from uuid import UUID

from ...domain.chat.entities import AgentContext, TherapyResponse


class ILLMService(ABC):
    """Interface for LLM services"""
    
    @abstractmethod
    async def generate_therapy_response(
        self, 
        context: AgentContext, 
        user_message: str
    ) -> TherapyResponse:
        """Generate a therapeutic response using the LLM"""
        pass
    
    @abstractmethod
    async def analyze_emotional_state(self, message: str) -> Dict[str, Any]:
        """Analyze the emotional content of a message"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM service is healthy"""
        pass
