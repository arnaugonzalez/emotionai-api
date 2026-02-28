"""
Domain Events

Events that represent important business events in the domain.
These enable decoupled communication between different parts of the system.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import UUID

from ..value_objects.user_profile import UserProfile


@dataclass(frozen=True)
class DomainEvent:
    """Base domain event"""
    event_id: str
    occurred_at: datetime
    event_type: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "occurred_at": self.occurred_at.isoformat(),
            "event_type": self.event_type
        }


@dataclass(frozen=True)
class UserCreatedEvent(DomainEvent):
    """Event fired when a new user is created"""
    user_id: UUID
    email: str
    
    def __post_init__(self):
        if not hasattr(self, 'event_type'):
            object.__setattr__(self, 'event_type', 'user_created')
        if not hasattr(self, 'occurred_at'):
            object.__setattr__(self, 'occurred_at', datetime.now(timezone.utc))
        if not hasattr(self, 'event_id'):
            import uuid
            object.__setattr__(self, 'event_id', str(uuid.uuid4()))


@dataclass(frozen=True)
class UserProfileUpdatedEvent(DomainEvent):
    """Event fired when user profile is updated"""
    user_id: UUID
    old_profile: UserProfile
    new_profile: UserProfile
    
    def __post_init__(self):
        if not hasattr(self, 'event_type'):
            object.__setattr__(self, 'event_type', 'user_profile_updated')
        if not hasattr(self, 'occurred_at'):
            object.__setattr__(self, 'occurred_at', datetime.now(timezone.utc))
        if not hasattr(self, 'event_id'):
            import uuid
            object.__setattr__(self, 'event_id', str(uuid.uuid4()))


@dataclass(frozen=True)
class AgentConversationStartedEvent(DomainEvent):
    """Event fired when an agent conversation starts"""
    user_id: UUID
    agent_type: str
    session_id: str
    
    def __post_init__(self):
        if not hasattr(self, 'event_type'):
            object.__setattr__(self, 'event_type', 'agent_conversation_started')
        if not hasattr(self, 'occurred_at'):
            object.__setattr__(self, 'occurred_at', datetime.now(timezone.utc))
        if not hasattr(self, 'event_id'):
            import uuid
            object.__setattr__(self, 'event_id', str(uuid.uuid4()))


@dataclass(frozen=True)
class EmotionalRecordCreatedEvent(DomainEvent):
    """Event fired when emotional record is created"""
    user_id: UUID
    emotion_type: str
    intensity: int
    context: str
    
    def __post_init__(self):
        if not hasattr(self, 'event_type'):
            object.__setattr__(self, 'event_type', 'emotional_record_created')
        if not hasattr(self, 'occurred_at'):
            object.__setattr__(self, 'occurred_at', datetime.now(timezone.utc))
        if not hasattr(self, 'event_id'):
            import uuid
            object.__setattr__(self, 'event_id', str(uuid.uuid4()))


@dataclass(frozen=True)
class UserDataTaggedEvent(DomainEvent):
    """Event fired when user data has been processed for intelligent tagging"""
    user_id: UUID
    data_type: str  # 'message', 'emotional_record', 'breathing_session'
    data_id: str
    extracted_tags: List[str]
    tag_confidence: float
    
    def __post_init__(self):
        if not hasattr(self, 'event_type'):
            object.__setattr__(self, 'event_type', 'user_data_tagged')
        if not hasattr(self, 'occurred_at'):
            object.__setattr__(self, 'occurred_at', datetime.now(timezone.utc))
        if not hasattr(self, 'event_id'):
            import uuid
            object.__setattr__(self, 'event_id', str(uuid.uuid4()))


@dataclass(frozen=True)
class UserProfileInsightsUpdatedEvent(DomainEvent):
    """Event fired when user profile is updated with new insights"""
    user_id: UUID
    insights_added: List[str]
    tags_updated: bool
    behavioral_patterns_detected: bool

    def __post_init__(self):
        if not hasattr(self, 'event_type'):
            object.__setattr__(self, 'event_type', 'user_profile_insights_updated')
        if not hasattr(self, 'occurred_at'):
            object.__setattr__(self, 'occurred_at', datetime.now(timezone.utc))
        if not hasattr(self, 'event_id'):
            import uuid
            object.__setattr__(self, 'event_id', str(uuid.uuid4())) 