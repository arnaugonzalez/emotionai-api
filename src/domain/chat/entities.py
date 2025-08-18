"""
Domain Entities for Chat System

Core business objects for conversations, messages, and agent interactions.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime


@dataclass
class Message:
    """A single message in a conversation"""
    id: str
    conversation_id: str
    user_id: UUID
    content: str
    message_type: str  # 'user', 'assistant', 'system'
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class Conversation:
    """A conversation session between a user and an agent"""
    id: str
    user_id: UUID
    agent_type: str  # 'therapy', 'wellness'
    title: str
    created_at: datetime
    last_message_at: datetime
    message_count: int
    is_active: bool


@dataclass
class AgentContext:
    """Context information for an agent to provide personalized responses"""
    user_id: UUID
    agent_type: str
    conversation_id: str
    recent_messages: list[Message]
    user_profile: Dict[str, Any]
    emotional_state: Optional[str] = None
    session_duration: Optional[int] = None
    crisis_indicators: list[str] = None
    
    def __post_init__(self):
        if self.crisis_indicators is None:
            self.crisis_indicators = []


@dataclass
class TherapyResponse:
    """A therapeutic response from the AI agent"""
    message: str
    agent_type: str
    conversation_id: str
    timestamp: datetime
    therapeutic_approach: str  # 'supportive', 'cognitive', 'mindfulness', 'crisis'
    emotional_tone: str  # 'empathetic', 'encouraging', 'calming', 'urgent'
    follow_up_suggestions: list[str]
    crisis_detected: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.follow_up_suggestions is None:
            self.follow_up_suggestions = []
