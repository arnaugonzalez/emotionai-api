"""
Domain Entity: User

This represents the core User business entity with all business logic
encapsulated within the entity itself.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from ..value_objects.agent_personality import AgentPersonality
from ..value_objects.user_profile import UserProfile
from ..events.domain_events import UserCreatedEvent, UserProfileUpdatedEvent


@dataclass
class User:
    """Core User domain entity with business logic"""
    
    id: UUID = field(default_factory=uuid4)
    email: str = ""
    hashed_password: str = ""
    is_active: bool = True
    agent_personality: AgentPersonality = field(default_factory=lambda: AgentPersonality.EMPATHETIC_SUPPORTIVE)
    profile: UserProfile = field(default_factory=UserProfile)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Domain events (to be published)
    _domain_events: List[Any] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """Initialize user after creation"""
        if not self.id:
            self.id = uuid4()
            self._add_domain_event(UserCreatedEvent(user_id=self.id, email=self.email))
    
    def update_profile(self, profile_data: Dict[str, Any]) -> None:
        """Update user profile with business validation"""
        old_profile = self.profile
        self.profile = UserProfile.from_dict(profile_data)
        self.updated_at = datetime.now(timezone.utc)
        
        # Domain event for profile updates
        self._add_domain_event(
            UserProfileUpdatedEvent(
                user_id=self.id,
                old_profile=old_profile,
                new_profile=self.profile
            )
        )
    
    def change_agent_personality(self, personality: AgentPersonality) -> None:
        """Change agent personality with business rules"""
        if self.agent_personality != personality:
            self.agent_personality = personality
            self.updated_at = datetime.now(timezone.utc)
    
    def deactivate(self) -> None:
        """Deactivate user account"""
        self.is_active = False
        self.updated_at = datetime.now(timezone.utc)
    
    def activate(self) -> None:
        """Activate user account"""
        self.is_active = True
        self.updated_at = datetime.now(timezone.utc)
    
    def is_profile_complete(self) -> bool:
        """Check if user profile is complete enough for personalized agents"""
        return self.profile.is_complete()
    
    def get_agent_preferences(self) -> Dict[str, Any]:
        """Get preferences for agent configuration"""
        return {
            "personality": self.agent_personality.value,
            "goals": self.profile.goals,
            "concerns": self.profile.concerns,
            "preferred_activities": self.profile.preferred_activities,
            "communication_style": self.profile.communication_style
        }
    
    def _add_domain_event(self, event: Any) -> None:
        """Add domain event to be published"""
        self._domain_events.append(event)
    
    def get_domain_events(self) -> List[Any]:
        """Get all domain events"""
        return self._domain_events.copy()
    
    def clear_domain_events(self) -> None:
        """Clear domain events after publishing"""
        self._domain_events.clear()
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id) 