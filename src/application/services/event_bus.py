"""
Event Bus Interface

This interface defines the contract for event publishing and subscription.
It enables decoupled communication through domain events.
"""

from abc import ABC, abstractmethod
from typing import Callable, Any, List
from uuid import UUID

from ...domain.events.domain_events import DomainEvent


class IEventBus(ABC):
    """Interface for event bus operations"""
    
    @abstractmethod
    async def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event
        
        Args:
            event: The domain event to publish
        """
        pass
    
    @abstractmethod
    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """
        Publish multiple domain events in batch
        
        Args:
            events: List of domain events to publish
        """
        pass
    
    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], Any]) -> None:
        """
        Subscribe to domain events of a specific type
        
        Args:
            event_type: Type of events to subscribe to
            handler: Function to handle the events
        """
        pass
    
    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable[[DomainEvent], Any]) -> None:
        """
        Unsubscribe from domain events
        
        Args:
            event_type: Type of events to unsubscribe from
            handler: The handler function to remove
        """
        pass
    
    @abstractmethod
    async def start(self) -> None:
        """Start the event bus service"""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the event bus service"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if event bus is healthy"""
        pass
    
    @abstractmethod
    async def get_pending_events(self, user_id: UUID) -> List[DomainEvent]:
        """
        Get pending events for a specific user
        
        Args:
            user_id: ID of the user to get events for
            
        Returns:
            List of pending domain events
        """
        pass
    
    @abstractmethod
    async def mark_event_processed(self, event_id: str) -> None:
        """
        Mark an event as processed
        
        Args:
            event_id: ID of the event to mark as processed
        """
        pass 