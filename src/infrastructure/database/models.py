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
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Agent-related fields
    agent_personality_data = Column(JSON, nullable=True)
    user_profile_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    conversations = relationship("ConversationModel", back_populates="user", cascade="all, delete-orphan")
    emotional_records = relationship("EmotionalRecordModel", back_populates="user", cascade="all, delete-orphan")
    breathing_sessions = relationship("BreathingSessionModel", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_active', 'is_active'),
        Index('idx_users_created_at', 'created_at'),
    )


class ConversationModel(Base):
    """SQLAlchemy model for Conversation entity"""
    __tablename__ = 'conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    agent_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=True)
    context_data = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="conversations")
    messages = relationship("MessageModel", back_populates="conversation", cascade="all, delete-orphan")


class MessageModel(Base):
    """SQLAlchemy model for conversation messages"""
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=False)
    content = Column(Text, nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    message_metadata = Column(JSON, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    # Intelligent tagging system
    tags = Column(JSONB, nullable=True)  # Semantic tags extracted from content
    tag_confidence = Column(Float, nullable=True)  # Confidence in tag extraction
    processed_for_tags = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    conversation = relationship("ConversationModel", back_populates="messages")
    
    # Indexes for tag-based search
    __table_args__ = (
        Index('idx_messages_tags', 'tags', postgresql_using='gin'),
        Index('idx_messages_role_tags', 'role', 'tags'),
        Index('idx_messages_created_at', 'created_at'),
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