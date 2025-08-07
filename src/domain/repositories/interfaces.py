"""
Repository Interfaces

Defines contracts for data access without implementation details.
These interfaces belong to the domain layer and are implemented in infrastructure.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..entities.user import User
from ..events.domain_events import DomainEvent


class IUserRepository(ABC):
    """Interface for user data access"""
    
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID"""
        pass
    
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        pass
    
    @abstractmethod
    async def save(self, user: User) -> User:
        """Save user (create or update)"""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete user"""
        pass
    
    @abstractmethod
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """List users with pagination"""
        pass
    
    @abstractmethod
    async def exists(self, email: str) -> bool:
        """Check if user exists by email"""
        pass


class IEmotionalRecordRepository(ABC):
    """Interface for emotional record data access"""
    
    @abstractmethod
    async def get_by_user_id(
        self, 
        user_id: UUID, 
        limit: Optional[int] = None,
        days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get emotional records for a user"""
        pass
    
    @abstractmethod
    async def save(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save emotional record"""
        pass
    
    @abstractmethod
    async def get_emotional_patterns(self, user_id: UUID) -> Dict[str, Any]:
        """Get emotional patterns analysis for user"""
        pass


class IBreathingSessionRepository(ABC):
    """Interface for breathing session data access"""
    
    @abstractmethod
    async def get_by_user_id(
        self, 
        user_id: UUID, 
        limit: Optional[int] = None,
        days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get breathing sessions for a user"""
        pass
    
    @abstractmethod
    async def save(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save breathing session"""
        pass
    
    @abstractmethod
    async def get_session_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """Get breathing session analytics for user"""
        pass


class IAgentConversationRepository(ABC):
    """Interface for agent conversation data access"""
    
    @abstractmethod
    async def save_conversation(
        self, 
        user_id: UUID, 
        agent_type: str, 
        conversation_data: Dict[str, Any]
    ) -> str:
        """Save conversation and return conversation ID"""
        pass
    
    @abstractmethod
    async def get_conversation_history(
        self, 
        user_id: UUID, 
        agent_type: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation history for user and agent type"""
        pass
    
    @abstractmethod
    async def get_conversation_summary(
        self, 
        user_id: UUID, 
        agent_type: str
    ) -> Optional[str]:
        """Get conversation summary for context"""
        pass


class IEventRepository(ABC):
    """Interface for domain event storage"""
    
    @abstractmethod
    async def save_event(self, event: DomainEvent) -> None:
        """Save domain event"""
        pass
    
    @abstractmethod
    async def get_events_by_user(
        self, 
        user_id: UUID, 
        event_types: Optional[List[str]] = None
    ) -> List[DomainEvent]:
        """Get domain events for a user"""
        pass
    
    @abstractmethod
    async def get_unprocessed_events(self) -> List[DomainEvent]:
        """Get events that haven't been processed"""
        pass
    
    @abstractmethod
    async def mark_event_processed(self, event_id: str) -> None:
        """Mark event as processed"""
        pass


class IAnalyticsRepository(ABC):
    """Interface for analytics and metrics data access"""
    
    @abstractmethod
    async def save_agent_interaction(
        self, 
        user_id: UUID, 
        agent_type: str, 
        interaction_data: Dict[str, Any]
    ) -> None:
        """Save agent interaction for analytics"""
        pass
    
    @abstractmethod
    async def get_user_analytics(self, user_id: UUID) -> Dict[str, Any]:
        """Get comprehensive user analytics"""
        pass
    
    @abstractmethod
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system-wide metrics"""
        pass 