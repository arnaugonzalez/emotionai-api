from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    
    # Agent-related fields
    agent_personality = Column(String, default="empathetic_supportive")
    profile_data = Column(JSON, default=dict)
    agent_preferences = Column(JSON, default=dict)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class EmotionalRecord(Base):
    __tablename__ = "emotional_records"
    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(DateTime, default=datetime.datetime.utcnow)  # Changed from 'date' to be more descriptive
    date = Column(DateTime, default=datetime.datetime.utcnow)  # Keep for backwards compatibility
    source = Column(String)
    description = Column(String)
    emotion = Column(String)
    emotion_type = Column(String)  # Additional field for standardized emotion types
    intensity = Column(Integer, default=5)  # 1-10 scale
    color = Column(String)
    context = Column(Text, nullable=True)  # Additional context information
    location = Column(String, nullable=True)  # Where the emotion was recorded
    notes = Column(Text, nullable=True)  # Additional notes
    customEmotionName = Column(String, nullable=True)
    customEmotionColor = Column(Integer, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # More descriptive name
    owner_id = Column(Integer, ForeignKey("users.id"))  # Keep for backwards compatibility
    owner = relationship("User")

class BreathingSession(Base):  # Renamed for consistency
    __tablename__ = "breathing_sessions"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)  # More descriptive
    date = Column(DateTime, default=datetime.datetime.utcnow)  # Keep for backwards compatibility
    pattern_name = Column(String)  # More descriptive
    pattern = Column(String)  # Keep for backwards compatibility
    duration_seconds = Column(Integer, default=0)  # Duration in seconds
    rating = Column(Float)
    comment = Column(String, nullable=True)
    session_data = Column(JSON, nullable=True)  # Additional session metadata
    user_id = Column(Integer, ForeignKey("users.id"))  # More descriptive name
    owner_id = Column(Integer, ForeignKey("users.id"))  # Keep for backwards compatibility
    owner = relationship("User")

# Keep the old name for backwards compatibility
BreathingSessionData = BreathingSession

class BreathingPattern(Base):
    __tablename__ = "breathing_patterns"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    inhaleSeconds = Column(Integer)
    holdSeconds = Column(Integer)
    exhaleSeconds = Column(Integer)
    cycles = Column(Integer)
    restSeconds = Column(Integer)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Can be global
    owner = relationship("User")

class CustomEmotion(Base):
    __tablename__ = "custom_emotions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    color = Column(Integer)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

class AiConversationMemory(Base):
    __tablename__ = "ai_conversation_memories"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    conversationId = Column(String)
    summary = Column(String)
    context = Column(String)
    tokensUsed = Column(Integer)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")

class DailyTokenUsage(Base):
    __tablename__ = "daily_token_usage"
    id = Column(Integer, primary_key=True, index=True)
    userId = Column(Integer, ForeignKey("users.id"))
    date = Column(DateTime)
    promptTokens = Column(Integer, default=0)
    completionTokens = Column(Integer, default=0)
    costInCents = Column(Float, default=0.0)
    owner_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User")