"""
Database Models for Infrastructure Layer

SQLAlchemy models that represent the persistence layer.
These models map to domain entities but contain database-specific concerns.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, Integer, Float, 
    ForeignKey, JSON, Index, UniqueConstraint, ARRAY
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .connection import Base


class UserModel(Base):
    """SQLAlchemy model for User entity"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Extended profile fields (added in migration 005)
    phone_number = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    occupation = Column(String(100), nullable=True)
    emergency_contact = Column(JSON, nullable=True)
    medical_conditions = Column(JSON, nullable=True)
    medications = Column(JSON, nullable=True)
    therapy_goals = Column(Text, nullable=True)
    preferred_communication_style = Column(String(50), nullable=True)
    
    # Therapy context and AI knowledge (added in migration 005)
    therapy_context = Column(JSONB, nullable=True)  # What AI knows about the user
    therapy_preferences = Column(JSON, nullable=True)  # User's therapy preferences
    ai_insights = Column(JSONB, nullable=True)  # AI-generated insights about user
    
    # Legacy JSON columns (will be replaced by new tables)
    agent_personality_data = Column(JSON, nullable=True)  # Legacy - will be moved to agent_personality table
    user_profile_data = Column(JSON, nullable=True)  # Legacy - will be moved to user_profile_data table
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    # Legal
    terms_accepted = Column(Boolean, default=False, nullable=False)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    conversations = relationship("ConversationModel", back_populates="user", cascade="all, delete-orphan")
    emotional_records = relationship("EmotionalRecordModel", back_populates="user", cascade="all, delete-orphan")
    breathing_sessions = relationship("BreathingSessionModel", back_populates="user", cascade="all, delete-orphan")
    profile_data = relationship("UserProfileDataModel", back_populates="user", uselist=False, cascade="all, delete-orphan")
    agent_personality = relationship("AgentPersonalityModel", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_username', 'username'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
        Index('idx_users_therapy_context', 'therapy_context', postgresql_using='gin'),
    )


class UserProfileDataModel(Base):
    """SQLAlchemy model for extended user profile data"""
    __tablename__ = 'user_profile_data'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    
    # Personality and preferences
    personality_type = Column(String(20), nullable=True)  # MBTI type
    relaxation_time = Column(String(50), nullable=True)  # Morning, Afternoon, Evening, Night, Various times
    selfcare_frequency = Column(String(50), nullable=True)  # Multiple times a day, Once a day, etc.
    relaxation_tools = Column(ARRAY(String), nullable=True)  # Array of selected tools
    has_previous_mental_health_app_experience = Column(Boolean, nullable=True)
    therapy_chat_history_preference = Column(String(50), nullable=True)
    country = Column(String(100), nullable=True)
    gender = Column(String(20), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="profile_data")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_profile_data_user_id', 'user_id'),
        Index('idx_user_profile_data_personality', 'personality_type'),
        Index('idx_user_profile_data_country', 'country'),
    )


class AgentPersonalityModel(Base):
    """SQLAlchemy model for AI agent personality and therapy context"""
    __tablename__ = 'agent_personality'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    
    # Agent personality settings
    agent_style = Column(String(50), nullable=True)  # Supportive, Direct, Analytical, etc.
    communication_tone = Column(String(50), nullable=True)  # Formal, Casual, Friendly, etc.
    therapy_approach = Column(String(50), nullable=True)  # CBT, DBT, Humanistic, etc.
    
    # User context for AI
    mood_patterns = Column(Text, nullable=True)
    stress_triggers = Column(Text, nullable=True)
    coping_strategies = Column(Text, nullable=True)
    progress_areas = Column(Text, nullable=True)
    
    # Therapy session preferences
    session_duration = Column(Integer, nullable=True)  # minutes
    session_frequency = Column(String(50), nullable=True)
    preferred_topics = Column(ARRAY(String), nullable=True)
    
    # AI insights and learning
    conversation_history_summary = Column(Text, nullable=True)
    user_response_patterns = Column(Text, nullable=True)
    effective_interventions = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="agent_personality")
    
    # Indexes
    __table_args__ = (
        Index('idx_agent_personality_user_id', 'user_id'),
        Index('idx_agent_personality_style', 'agent_style'),
        Index('idx_agent_personality_approach', 'therapy_approach'),
    )


class ConversationModel(Base):
    """SQLAlchemy model for Conversation entity"""
    __tablename__ = 'conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    agent_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    context_data = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_message_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="conversations")
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_conversations_user_agent', 'user_id', 'agent_type'),
        Index('idx_conversations_active', 'is_active'),
        Index('idx_conversations_last_message', 'last_message_at'),
    )


class MessageModel(Base):
    """SQLAlchemy model for conversation messages"""
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(String(20), nullable=False, index=True)  # 'user', 'assistant', 'system'
    message_metadata = Column(JSON, nullable=True)
    
    # Intelligent tagging system
    tags = Column(JSONB, nullable=True)  # Semantic tags extracted from content
    tag_confidence = Column(Float, nullable=True)  # Confidence in tag extraction
    processed_for_tags = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")
    
    # Indexes for tag-based search
    __table_args__ = (
        Index('idx_messages_conversation', 'conversation_id'),
        Index('idx_messages_user', 'user_id'),
        Index('idx_messages_type', 'message_type'),
        Index('idx_messages_timestamp', 'timestamp'),
        Index('idx_messages_tags', 'tags', postgresql_using='gin'),
    )


class EmotionalRecordModel(Base):
    """SQLAlchemy model for emotional records"""
    __tablename__ = 'emotional_records'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    emotion = Column(String(50), nullable=False)
    intensity = Column(Integer, nullable=False)  # 1-10 scale
    triggers = Column(JSON, nullable=True)
    notes = Column(Text, nullable=True)
    context_data = Column(JSON, nullable=True)
    
    # Intelligent tagging system
    tags = Column(JSONB, nullable=True)  # Semantic tags for emotional context
    tag_confidence = Column(Float, nullable=True)
    processed_for_tags = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="emotional_records")
    
    # Indexes for tag-based search
    __table_args__ = (
        Index('idx_emotional_records_tags', 'tags', postgresql_using='gin'),
        Index('idx_emotional_records_emotion_tags', 'emotion', 'tags'),
        Index('idx_emotional_records_user_tags', 'user_id', 'tags'),
        Index('idx_emotional_records_recorded_at', 'recorded_at'),
    )


class BreathingSessionModel(Base):
    """SQLAlchemy model for breathing sessions"""
    __tablename__ = 'breathing_sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    pattern_name = Column(String(100), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    completed = Column(Boolean, default=False, nullable=False)
    effectiveness_rating = Column(Integer, nullable=True)  # 1-5 scale
    notes = Column(Text, nullable=True)
    session_data = Column(JSON, nullable=True)
    
    # Intelligent tagging system
    tags = Column(JSONB, nullable=True)  # Semantic tags for session context
    tag_confidence = Column(Float, nullable=True)
    processed_for_tags = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="breathing_sessions")
    
    # Indexes for tag-based search
    __table_args__ = (
        Index('idx_breathing_sessions_tags', 'tags', postgresql_using='gin'),
        Index('idx_breathing_sessions_user_tags', 'user_id', 'tags'),
        Index('idx_breathing_sessions_completed', 'completed'),
        Index('idx_breathing_sessions_started_at', 'started_at'),
    )


class BreathingPatternModel(Base):
    """SQLAlchemy model for breathing patterns"""
    __tablename__ = 'breathing_patterns'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)  # NULL for global patterns
    name = Column(String(100), nullable=False)
    inhale_seconds = Column(Integer, nullable=False)
    hold_seconds = Column(Integer, nullable=False, default=0)
    exhale_seconds = Column(Integer, nullable=False)
    cycles = Column(Integer, nullable=False, default=4)
    rest_seconds = Column(Integer, nullable=False, default=0)
    description = Column(Text, nullable=True)
    is_preset = Column(Boolean, default=False, nullable=False)  # True for system presets
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Intelligent tagging system
    tags = Column(JSONB, nullable=True)  # Semantic tags for pattern context
    tag_confidence = Column(Float, nullable=True)
    processed_for_tags = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel", backref="breathing_patterns")
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_breathing_patterns_user', 'user_id'),
        Index('idx_breathing_patterns_preset', 'is_preset'),
        Index('idx_breathing_patterns_tags', 'tags', postgresql_using='gin'),
        Index('idx_breathing_patterns_name', 'name'),
    )


class CustomEmotionModel(Base):
    """SQLAlchemy model for custom emotions"""
    __tablename__ = 'custom_emotions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = Column(String(50), nullable=False)
    color = Column(Integer, nullable=False)  # Color as integer for Flutter compatibility
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Intelligent tagging system
    tags = Column(JSONB, nullable=True)  # Semantic tags for emotion context
    tag_confidence = Column(Float, nullable=True)
    processed_for_tags = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel", backref="custom_emotions")
    
    # Constraints and indexes
    __table_args__ = (
        Index('idx_custom_emotions_user', 'user_id'),
        Index('idx_custom_emotions_name', 'name'),
        Index('idx_custom_emotions_tags', 'tags', postgresql_using='gin'),
        UniqueConstraint('user_id', 'name', name='uq_user_emotion_name'),
    )


class DailySuggestionModel(Base):
    """Stores daily suggestions generated by LLM for a user"""
    __tablename__ = 'daily_suggestions'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    suggestions = Column(JSONB, nullable=False, default=list)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship('UserModel')

    __table_args__ = (
        UniqueConstraint('user_id', 'date', name='uq_daily_suggestions_user_date'),
        Index('idx_daily_suggestions_user_date', 'user_id', 'date'),
    )


class DomainEventModel(Base):
    """SQLAlchemy model for domain events"""
    __tablename__ = 'domain_events'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False)
    aggregate_id = Column(String(100), nullable=True)
    aggregate_type = Column(String(50), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Processing status
    processed = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserProfileModel(Base):
    """SQLAlchemy model for user knowledge profiles"""
    __tablename__ = 'user_profiles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, unique=True)
    
    # Aggregated tag data
    frequent_tags = Column(JSONB, nullable=True)  # Most common tags with frequencies
    tag_categories = Column(JSONB, nullable=True)  # Categorized tags (emotional, behavioral, etc.)
    tag_trends = Column(JSONB, nullable=True)  # Tag usage trends over time
    
    # User insights
    personality_insights = Column(JSONB, nullable=True)  # LLM-generated insights
    behavioral_patterns = Column(JSONB, nullable=True)  # Detected patterns
    preferences = Column(JSONB, nullable=True)  # User preferences based on interactions
    
    # Statistics
    total_interactions = Column(Integer, default=0, nullable=False)
    unique_tags_count = Column(Integer, default=0, nullable=False)
    last_tag_analysis = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("UserModel")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_profiles_user_id', 'user_id'),
        Index('idx_user_profiles_frequent_tags', 'frequent_tags', postgresql_using='gin'),
        Index('idx_user_profiles_updated_at', 'updated_at'),
    )


class TagSemanticModel(Base):
    """SQLAlchemy model for tag semantic relationships and similarities"""
    __tablename__ = 'tag_semantics'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tag = Column(String(100), nullable=False)
    category = Column(String(50), nullable=True)  # emotional, behavioral, contextual, etc.
    
    # Semantic data
    similar_tags = Column(JSONB, nullable=True)  # Tags with similarity scores
    synonyms = Column(JSONB, nullable=True)  # Synonym tags
    related_concepts = Column(JSONB, nullable=True)  # Related concepts from LLM
    
    # Usage statistics
    usage_count = Column(Integer, default=1, nullable=False)
    unique_users = Column(Integer, default=1, nullable=False)
    
    # Timestamps
    first_seen = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_tag_semantics_tag', 'tag'),
        Index('idx_tag_semantics_category', 'category'),
        Index('idx_tag_semantics_similar_tags', 'similar_tags', postgresql_using='gin'),
        UniqueConstraint('tag', name='uq_tag_semantics_tag'),
    ) 


class TokenUsageModel(Base):
    """Tracks LLM token usage per user and interaction"""
    __tablename__ = 'token_usage'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False)  # chat, tagging_emotional_record, tagging_breathing_session
    model = Column(String(100), nullable=True)
    data_id = Column(String(100), nullable=True)  # conversation_id, record_id, etc.
    
    tokens_total = Column(Integer, nullable=False)
    tokens_prompt = Column(Integer, nullable=False, default=0)
    tokens_completion = Column(Integer, nullable=False, default=0)
    
    usage_metadata = Column(JSONB, nullable=True)  # renamed from 'metadata' to avoid SQLAlchemy reserved name conflict
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    user = relationship('UserModel')
    
    __table_args__ = (
        Index('idx_token_usage_user_created', 'user_id', 'created_at'),
        Index('idx_token_usage_type', 'interaction_type'),
    )