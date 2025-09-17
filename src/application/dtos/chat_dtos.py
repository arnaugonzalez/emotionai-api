"""
Data Transfer Objects for Chat Operations

DTOs provide a clean interface for data transfer between layers
without exposing internal domain structures.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone


@dataclass(frozen=True)
class ChatRequest:
    """Request DTO for agent chat"""
    user_id: UUID
    message: str
    agent_type: str = "therapy"
    context: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        # Validate message length
        if not self.message or len(self.message.strip()) == 0:
            raise ValueError("Message cannot be empty")
        
        if len(self.message) > 2000:
            raise ValueError("Message too long (max 2000 characters)")
        
        # Validate agent type
        valid_types = ["therapy", "wellness"]
        if self.agent_type not in valid_types:
            raise ValueError(f"Invalid agent type. Must be one of: {valid_types}")


@dataclass(frozen=True)
class ChatResponse:
    """Response DTO for agent chat"""
    message: str
    agent_type: str
    user_message: str
    conversation_id: Optional[str] = None
    timestamp: datetime = None
    context_used: Optional[Dict[str, Any]] = None
    is_crisis_response: bool = False  # Kept for therapy refinement (not standalone crisis detection)
    
    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, 'timestamp', datetime.now(timezone.utc))
    
    @classmethod
    def create_crisis_response(cls, crisis_message: str) -> 'ChatResponse':
        """Create a crisis response for urgent therapeutic situations (therapy refinement)"""
        return cls(
            message=crisis_message,
            agent_type="crisis",
            user_message="[Crisis content detected]",
            is_crisis_response=True
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "message": self.message,
            "agent_type": self.agent_type,
            "user_message": self.user_message,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "is_crisis_response": self.is_crisis_response
        }


@dataclass(frozen=True)
class AgentStatusRequest:
    """Request DTO for agent status"""
    user_id: UUID
    agent_type: str = "therapy"


@dataclass(frozen=True)
class AgentStatusResponse:
    """Response DTO for agent status"""
    active: bool
    agent_type: str
    last_interaction: Optional[datetime] = None
    memory_summary: Optional[str] = None
    personality: str = "empathetic_supportive"
    conversation_length: int = 0
    session_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "active": self.active,
            "agent_type": self.agent_type,
            "last_interaction": self.last_interaction.isoformat() if self.last_interaction else None,
            "memory_summary": self.memory_summary,
            "personality": self.personality,
            "conversation_length": self.conversation_length,
            "session_count": self.session_count
        }


@dataclass(frozen=True)
class EmotionalRecordRequest:
    """Request DTO for adding emotional records"""
    user_id: UUID
    emotion_type: str
    intensity: int
    context: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    
    def __post_init__(self):
        # Validate intensity
        if not (1 <= self.intensity <= 10):
            raise ValueError("Intensity must be between 1 and 10")
        
        # Validate emotion type
        if not self.emotion_type or len(self.emotion_type.strip()) == 0:
            raise ValueError("Emotion type cannot be empty")


@dataclass(frozen=True)
class BreathingSessionRequest:
    """Request DTO for adding breathing sessions"""
    user_id: UUID
    pattern_name: str
    duration_seconds: int
    rating: Optional[float] = None
    notes: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        # Validate duration
        if self.duration_seconds < 0:
            raise ValueError("Duration cannot be negative")
        
        # Validate rating if provided
        if self.rating is not None and not (1.0 <= self.rating <= 10.0):
            raise ValueError("Rating must be between 1.0 and 10.0")


@dataclass(frozen=True)
class UserProfileUpdateRequest:
    """Request DTO for updating user profile"""
    user_id: UUID
    profile_data: Dict[str, Any]
    
    def __post_init__(self):
        if not self.profile_data:
            raise ValueError("Profile data cannot be empty")


@dataclass(frozen=True)
class UserRegistrationRequest:
    """Request DTO for user registration"""
    email: str
    password: str
    first_name: str
    last_name: str
    
    def __post_init__(self):
        # Basic validation
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email address is required")
        
        if not self.password or len(self.password) < 6:
            raise ValueError("Password must be at least 6 characters")
        
        if not self.first_name or not self.last_name:
            raise ValueError("First name and last name are required")


@dataclass(frozen=True)
class UserLoginRequest:
    """Request DTO for user login"""
    email: str
    password: str
    
    def __post_init__(self):
        # Basic validation
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email address is required")
        
        if not self.password:
            raise ValueError("Password is required")


@dataclass(frozen=True)
class TokenResponse:
    """Response DTO for authentication tokens"""
    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "access_token": self.access_token,
            "token_type": self.token_type,
            "expires_in": self.expires_in,
            "user": self.user
        }


@dataclass(frozen=True)
class ConversationHistoryResponse:
    """Response DTO for conversation history"""
    id: str
    agent_type: str
    title: str
    created_at: datetime
    last_message_at: datetime
    message_count: int
    is_active: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "id": self.id,
            "agent_type": self.agent_type,
            "title": self.title,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "message_count": self.message_count,
            "is_active": self.is_active
        }


# Crisis detection system has been removed in favor of intelligent tagging system 