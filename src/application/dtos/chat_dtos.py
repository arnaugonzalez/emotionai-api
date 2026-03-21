"""
Data Transfer Objects for Chat Operations

DTOs provide a clean interface for data transfer between layers
without exposing internal domain structures.

All DTOs use Pydantic v2 BaseModel so that validation errors surface
as pydantic.ValidationError and produce structured HTTP 422 responses
via FastAPI — instead of bare ValueError from dataclass __post_init__.
"""

from typing import Dict, Any, Optional, Literal
from uuid import UUID
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Self


class ChatRequest(BaseModel):
    """Request DTO for agent chat"""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    message: str = Field(..., min_length=1, max_length=2000)
    agent_type: Literal["therapy", "wellness"] = "therapy"
    context: Optional[Dict[str, Any]] = None

    @field_validator("message")
    @classmethod
    def message_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return v


class ChatResponse(BaseModel):
    """Response DTO for agent chat"""

    model_config = ConfigDict(frozen=True)

    message: str
    agent_type: str
    user_message: str
    conversation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    context_used: Optional[Dict[str, Any]] = None
    is_crisis_response: bool = False  # Kept for therapy refinement (not standalone crisis detection)

    @classmethod
    def create_crisis_response(cls, crisis_message: str) -> "ChatResponse":
        """Create a crisis response for urgent therapeutic situations (therapy refinement)"""
        return cls(
            message=crisis_message,
            agent_type="crisis",
            user_message="[Crisis content detected]",
            is_crisis_response=True,
        )


class AgentStatusRequest(BaseModel):
    """Request DTO for agent status"""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    agent_type: str = "therapy"


class AgentStatusResponse(BaseModel):
    """Response DTO for agent status"""

    model_config = ConfigDict(frozen=True)

    active: bool
    agent_type: str
    last_interaction: Optional[datetime] = None
    memory_summary: Optional[str] = None
    personality: str = "empathetic_supportive"
    conversation_length: int = 0
    session_count: int = 0


class EmotionalRecordRequest(BaseModel):
    """Request DTO for adding emotional records"""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    emotion_type: str
    intensity: int = Field(..., ge=1, le=10)
    context: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("emotion_type")
    @classmethod
    def emotion_type_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Emotion type cannot be empty")
        return v


class BreathingSessionRequest(BaseModel):
    """Request DTO for adding breathing sessions"""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    pattern_name: str
    duration_seconds: int = Field(..., ge=0)
    rating: Optional[float] = Field(None, ge=1.0, le=10.0)
    notes: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None


class UserProfileUpdateRequest(BaseModel):
    """Request DTO for updating user profile"""

    model_config = ConfigDict(frozen=True)

    user_id: UUID
    profile_data: Dict[str, Any]

    @model_validator(mode="after")
    def profile_data_not_empty(self) -> Self:
        if not self.profile_data:
            raise ValueError("Profile data cannot be empty")
        return self


class UserRegistrationRequest(BaseModel):
    """Request DTO for user registration"""

    model_config = ConfigDict(frozen=True)

    email: str
    password: str = Field(..., min_length=6)
    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v: str) -> str:
        if not v or "@" not in v:
            raise ValueError("Valid email address is required")
        return v


class UserLoginRequest(BaseModel):
    """Request DTO for user login"""

    model_config = ConfigDict(frozen=True)

    email: str
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def email_must_be_valid(cls, v: str) -> str:
        if not v or "@" not in v:
            raise ValueError("Valid email address is required")
        return v


class TokenResponse(BaseModel):
    """Response DTO for authentication tokens"""

    model_config = ConfigDict(frozen=True)

    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]


class ConversationHistoryResponse(BaseModel):
    """Response DTO for conversation history"""

    model_config = ConfigDict(frozen=True)

    id: str
    agent_type: str
    title: str
    created_at: datetime
    last_message_at: datetime
    message_count: int
    is_active: bool = True


# Crisis detection system has been removed in favor of intelligent tagging system
