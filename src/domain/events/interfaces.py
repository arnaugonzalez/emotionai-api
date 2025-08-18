"""
Event Repository Interfaces (feature-scoped)
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from .domain_events import DomainEvent


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
        event_types: Optional[List[str]] = None,
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


