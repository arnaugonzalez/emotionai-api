from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool
    agent_personality: Optional[str] = "empathetic_supportive"
    profile_data: Optional[Dict[str, Any]] = {}
    agent_preferences: Optional[Dict[str, Any]] = {}
    created_at: Optional[datetime.datetime] = None

    class Config:
        orm_mode = True

class EmotionalRecordBase(BaseModel):
    source: str
    description: str
    emotion: str
    color: str
    emotion_type: Optional[str] = None
    intensity: Optional[int] = 5
    context: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    customEmotionName: Optional[str] = None
    customEmotionColor: Optional[int] = None

class EmotionalRecordCreate(EmotionalRecordBase):
    pass

class EmotionalRecord(EmotionalRecordBase):
    id: int
    owner_id: int
    user_id: Optional[int] = None
    recorded_at: datetime.datetime
    date: datetime.datetime  # Keep for backwards compatibility

    class Config:
        orm_mode = True

class BreathingSessionDataBase(BaseModel):
    pattern: str
    pattern_name: Optional[str] = None
    duration_seconds: Optional[int] = 0
    rating: float
    comment: Optional[str] = None
    session_data: Optional[Dict[str, Any]] = None

class BreathingSessionDataCreate(BreathingSessionDataBase):
    pass

class BreathingSessionData(BreathingSessionDataBase):
    id: int
    owner_id: int
    user_id: Optional[int] = None
    created_at: datetime.datetime
    date: datetime.datetime  # Keep for backwards compatibility

    class Config:
        orm_mode = True

class BreathingPatternBase(BaseModel):
    name: str
    inhaleSeconds: int
    holdSeconds: int
    exhaleSeconds: int
    cycles: int
    restSeconds: int

class BreathingPatternCreate(BreathingPatternBase):
    pass

class BreathingPattern(BreathingPatternBase):
    id: int
    owner_id: Optional[int] = None

    class Config:
        orm_mode = True

class CustomEmotionBase(BaseModel):
    name: str
    color: int

class CustomEmotionCreate(CustomEmotionBase):
    pass

class CustomEmotion(CustomEmotionBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

class AiConversationMemoryBase(BaseModel):
    conversationId: str
    summary: str
    context: str
    tokensUsed: int

class AiConversationMemoryCreate(AiConversationMemoryBase):
    pass

class AiConversationMemory(AiConversationMemoryBase):
    id: int
    owner_id: int
    timestamp: datetime.datetime

    class Config:
        orm_mode = True

class DailyTokenUsageBase(BaseModel):
    userId: int
    date: datetime.datetime
    promptTokens: int
    completionTokens: int
    costInCents: float

class DailyTokenUsageCreate(DailyTokenUsageBase):
    pass

class DailyTokenUsage(DailyTokenUsageBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True

class AgentPersonalityUpdate(BaseModel):
    personality: str

class AgentProfileUpdate(BaseModel):
    profile_data: Dict[str, Any]

class AgentPreferencesUpdate(BaseModel):
    agent_preferences: Dict[str, Any]

class UserProfileData(BaseModel):
    goals: Optional[List[str]] = []
    concerns: Optional[List[str]] = []
    preferred_activities: Optional[List[str]] = []
    therapy_goals: Optional[List[str]] = []
    wellness_goals: Optional[List[str]] = []
    coping_strategies: Optional[List[str]] = []
    mindfulness_practices: Optional[List[str]] = []

class AgentContextUpdate(BaseModel):
    context_data: Dict[str, Any]