from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

Base = declarative_base()

# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Mental health profile
    profile_data = Column(JSON)  # Stores user preferences, goals, etc.
    
    # Agent configuration
    agent_personality = Column(String, default="empathetic_supportive")
    agent_preferences = Column(JSON)  # Agent customization settings
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active = Column(DateTime(timezone=True))

class EmotionalRecord(Base):
    __tablename__ = "emotional_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    emotion_type = Column(String, nullable=False)
    intensity = Column(Integer, nullable=False)  # 1-10 scale
    context = Column(Text)
    location = Column(String)
    notes = Column(Text)
    
    # Metadata
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BreathingSession(Base):
    __tablename__ = "breathing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    pattern_name = Column(String, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    session_data = Column(JSON)  # Pattern details, ratings, etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Pydantic Models for API
class UserBase(BaseModel):
    email: str
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    profile_data: Optional[Dict[str, Any]] = None
    agent_personality: Optional[str] = None
    agent_preferences: Optional[Dict[str, Any]] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    is_verified: bool
    profile_data: Optional[Dict[str, Any]] = None
    agent_personality: str
    agent_preferences: Optional[Dict[str, Any]] = None
    created_at: datetime
    last_active: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class EmotionalRecordCreate(BaseModel):
    emotion_type: str
    intensity: int = Field(ge=1, le=10)
    context: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class EmotionalRecordResponse(BaseModel):
    id: int
    user_id: int
    emotion_type: str
    intensity: int
    context: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    recorded_at: datetime
    
    class Config:
        from_attributes = True

class BreathingSessionCreate(BaseModel):
    pattern_name: str
    duration_seconds: int
    session_data: Optional[Dict[str, Any]] = None

class BreathingSessionResponse(BaseModel):
    id: int
    user_id: int
    pattern_name: str
    duration_seconds: int
    session_data: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True 