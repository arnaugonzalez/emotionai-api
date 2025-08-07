"""
Agent Service Interface

This interface defines the contract for agent services in the application layer.
It abstracts away the implementation details of agent management.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from uuid import UUID

from ..dtos.chat_dtos import AgentStatusResponse
from ...domain.value_objects.agent_personality import AgentPersonality


class IAgentService(ABC):
    """Interface for agent service operations"""
    
    @abstractmethod
    async def get_or_create_agent(
        self, 
        user_id: UUID, 
        agent_type: str,
        personality: AgentPersonality,
        context: Dict[str, Any]
    ) -> Any:
        """Get existing agent or create new one for user"""
        pass
    
    @abstractmethod
    async def process_message(
        self,
        user_id: UUID,
        agent_type: str,
        message: str,
        context: Dict[str, Any]
    ) -> str:
        """Process message with user's agent"""
        pass
    
    @abstractmethod
    async def get_agent_status(
        self,
        user_id: UUID,
        agent_type: str
    ) -> AgentStatusResponse:
        """Get status of user's agent"""
        pass
    
    @abstractmethod
    async def clear_agent_memory(
        self,
        user_id: UUID,
        agent_type: str
    ) -> bool:
        """Clear agent's conversation memory"""
        pass
    
    @abstractmethod
    async def update_agent_context(
        self,
        user_id: UUID,
        agent_type: str,
        context_data: Dict[str, Any]
    ) -> bool:
        """Update agent context with new information"""
        pass
    
    @abstractmethod
    async def get_active_agent_count(self) -> Dict[str, int]:
        """Get count of active agents by type"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if agent service is healthy"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup agent service resources"""
        pass 