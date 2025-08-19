"""Initial database schema with all models and example data

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-08-18 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime, timezone
import uuid

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables and insert example data"""
    
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('date_of_birth', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('occupation', sa.String(length=100), nullable=True),
        sa.Column('emergency_contact', sa.JSON(), nullable=True),
        sa.Column('medical_conditions', sa.JSON(), nullable=True),
        sa.Column('medications', sa.JSON(), nullable=True),
        sa.Column('therapy_goals', sa.Text(), nullable=True),
        sa.Column('preferred_communication_style', sa.String(length=50), nullable=True),
        sa.Column('therapy_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('therapy_preferences', sa.JSON(), nullable=True),
        sa.Column('ai_insights', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('agent_personality_data', sa.JSON(), nullable=True),
        sa.Column('user_profile_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_profile_data table
    op.create_table('user_profile_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('personality_type', sa.String(length=20), nullable=True),
        sa.Column('relaxation_time', sa.String(length=50), nullable=True),
        sa.Column('selfcare_frequency', sa.String(length=50), nullable=True),
        sa.Column('relaxation_tools', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('has_previous_mental_health_app_experience', sa.Boolean(), nullable=True),
        sa.Column('therapy_chat_history_preference', sa.String(length=50), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # Create agent_personality table
    op.create_table('agent_personality',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_style', sa.String(length=50), nullable=True),
        sa.Column('communication_tone', sa.String(length=50), nullable=True),
        sa.Column('therapy_approach', sa.String(length=50), nullable=True),
        sa.Column('mood_patterns', sa.Text(), nullable=True),
        sa.Column('stress_triggers', sa.Text(), nullable=True),
        sa.Column('coping_strategies', sa.Text(), nullable=True),
        sa.Column('progress_areas', sa.Text(), nullable=True),
        sa.Column('session_duration', sa.Integer(), nullable=True),
        sa.Column('session_frequency', sa.String(length=50), nullable=True),
        sa.Column('preferred_topics', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('conversation_history_summary', sa.Text(), nullable=True),
        sa.Column('user_response_patterns', sa.Text(), nullable=True),
        sa.Column('effective_interventions', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # Create conversations table
    op.create_table('conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('message_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_message_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create messages table
    op.create_table('messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('tag_confidence', sa.Float(), nullable=True),
        sa.Column('processed_for_tags', sa.Boolean(), nullable=False, default=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create emotional_records table
    op.create_table('emotional_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('emotion', sa.String(length=50), nullable=False),
        sa.Column('intensity', sa.Integer(), nullable=False),
        sa.Column('triggers', sa.JSON(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('context_data', sa.JSON(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('tag_confidence', sa.Float(), nullable=True),
        sa.Column('processed_for_tags', sa.Boolean(), nullable=False, default=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create breathing_sessions table
    op.create_table('breathing_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pattern_name', sa.String(length=100), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False, default=False),
        sa.Column('effectiveness_rating', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('session_data', sa.JSON(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('tag_confidence', sa.Float(), nullable=True),
        sa.Column('processed_for_tags', sa.Boolean(), nullable=False, default=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create breathing_patterns table
    op.create_table('breathing_patterns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('inhale_seconds', sa.Integer(), nullable=False),
        sa.Column('hold_seconds', sa.Integer(), nullable=False, default=0),
        sa.Column('exhale_seconds', sa.Integer(), nullable=False),
        sa.Column('cycles', sa.Integer(), nullable=False, default=4),
        sa.Column('rest_seconds', sa.Integer(), nullable=False, default=0),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_preset', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('tag_confidence', sa.Float(), nullable=True),
        sa.Column('processed_for_tags', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create custom_emotions table
    op.create_table('custom_emotions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False),
        sa.Column('color', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('tags', postgresql.JSONB(), nullable=True),
        sa.Column('tag_confidence', sa.Float(), nullable=True),
        sa.Column('processed_for_tags', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'name', name='uq_user_emotion_name')
    )
    
    # Create domain_events table
    op.create_table('domain_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('aggregate_id', sa.String(length=100), nullable=True),
        sa.Column('aggregate_type', sa.String(length=50), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('processed', sa.Boolean(), nullable=False, default=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create user_profiles table
    op.create_table('user_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('frequent_tags', postgresql.JSONB(), nullable=True),
        sa.Column('tag_categories', postgresql.JSONB(), nullable=True),
        sa.Column('tag_trends', postgresql.JSONB(), nullable=True),
        sa.Column('personality_insights', postgresql.JSONB(), nullable=True),
        sa.Column('behavioral_patterns', postgresql.JSONB(), nullable=True),
        sa.Column('preferences', postgresql.JSONB(), nullable=True),
        sa.Column('total_interactions', sa.Integer(), nullable=False, default=0),
        sa.Column('unique_tags_count', sa.Integer(), nullable=False, default=0),
        sa.Column('last_tag_analysis', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # Create tag_semantics table
    op.create_table('tag_semantics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tag', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('similar_tags', postgresql.JSONB(), nullable=True),
        sa.Column('synonyms', postgresql.JSONB(), nullable=True),
        sa.Column('related_concepts', postgresql.JSONB(), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=False, default=1),
        sa.Column('unique_users', sa.Integer(), nullable=False, default=1),
        sa.Column('first_seen', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tag')
    )
    
    # Create token_usage table
    op.create_table('token_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interaction_type', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('data_id', sa.String(length=100), nullable=True),
        sa.Column('tokens_total', sa.Integer(), nullable=False),
        sa.Column('tokens_prompt', sa.Integer(), nullable=False, default=0),
        sa.Column('tokens_completion', sa.Integer(), nullable=False, default=0),
        sa.Column('usage_metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_active', 'users', ['is_active'])
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    op.create_index('idx_users_therapy_context', 'users', ['therapy_context'], postgresql_using='gin')
    
    op.create_index('idx_user_profile_data_user_id', 'user_profile_data', ['user_id'])
    op.create_index('idx_user_profile_data_personality', 'user_profile_data', ['personality_type'])
    op.create_index('idx_user_profile_data_country', 'user_profile_data', ['country'])
    
    op.create_index('idx_agent_personality_user_id', 'agent_personality', ['user_id'])
    op.create_index('idx_agent_personality_style', 'agent_personality', ['agent_style'])
    op.create_index('idx_agent_personality_approach', 'agent_personality', ['therapy_approach'])
    
    op.create_index('idx_conversations_user_agent', 'conversations', ['user_id', 'agent_type'])
    op.create_index('idx_conversations_active', 'conversations', ['is_active'])
    op.create_index('idx_conversations_last_message', 'conversations', ['last_message_at'])
    
    op.create_index('idx_messages_conversation', 'messages', ['conversation_id'])
    op.create_index('idx_messages_user', 'messages', ['user_id'])
    op.create_index('idx_messages_type', 'messages', ['message_type'])
    op.create_index('idx_messages_timestamp', 'messages', ['timestamp'])
    op.create_index('idx_messages_tags', 'messages', ['tags'], postgresql_using='gin')
    
    op.create_index('idx_emotional_records_tags', 'emotional_records', ['tags'], postgresql_using='gin')
    op.create_index('idx_emotional_records_emotion_tags', 'emotional_records', ['emotion', 'tags'])
    op.create_index('idx_emotional_records_user_tags', 'emotional_records', ['user_id', 'tags'])
    op.create_index('idx_emotional_records_recorded_at', 'emotional_records', ['recorded_at'])
    
    op.create_index('idx_breathing_sessions_tags', 'breathing_sessions', ['tags'], postgresql_using='gin')
    op.create_index('idx_breathing_sessions_user_tags', 'breathing_sessions', ['user_id', 'tags'])
    op.create_index('idx_breathing_sessions_completed', 'breathing_sessions', ['completed'])
    op.create_index('idx_breathing_sessions_started_at', 'breathing_sessions', ['started_at'])
    
    op.create_index('idx_breathing_patterns_user', 'breathing_patterns', ['user_id'])
    op.create_index('idx_breathing_patterns_preset', 'breathing_patterns', ['is_preset'])
    op.create_index('idx_breathing_patterns_tags', 'breathing_patterns', ['tags'], postgresql_using='gin')
    op.create_index('idx_breathing_patterns_name', 'breathing_patterns', ['name'])
    
    op.create_index('idx_custom_emotions_user', 'custom_emotions', ['user_id'])
    op.create_index('idx_custom_emotions_name', 'custom_emotions', ['name'])
    op.create_index('idx_custom_emotions_tags', 'custom_emotions', ['tags'], postgresql_using='gin')
    
    op.create_index('idx_user_profiles_user_id', 'user_profiles', ['user_id'])
    op.create_index('idx_user_profiles_frequent_tags', 'user_profiles', ['frequent_tags'], postgresql_using='gin')
    op.create_index('idx_user_profiles_updated_at', 'user_profiles', ['updated_at'])
    
    op.create_index('idx_tag_semantics_tag', 'tag_semantics', ['tag'])
    op.create_index('idx_tag_semantics_category', 'tag_semantics', ['category'])
    op.create_index('idx_tag_semantics_similar_tags', 'tag_semantics', ['similar_tags'], postgresql_using='gin')
    
    op.create_index('idx_token_usage_user_created', 'token_usage', ['user_id', 'created_at'])
    op.create_index('idx_token_usage_type', 'token_usage', ['interaction_type'])
    
    # Insert example data
    connection = op.get_bind()
    
    # Example user
    user_id = str(uuid.uuid4())
    connection.execute(sa.text("""
        INSERT INTO users (id, email, username, hashed_password, first_name, last_name, 
                          phone_number, address, occupation, is_active, is_verified,
                          created_at, updated_at)
        VALUES (:user_id, 'john.doe@example.com', 'johndoe', 
                '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK2i', 
                'John', 'Doe', '+1234567890', '123 Main St, City, State', 'Software Developer', 
                true, true, NOW(), NOW())
    """), {'user_id': user_id})
    
    # Example user profile data
    connection.execute(sa.text("""
        INSERT INTO user_profile_data (id, user_id, personality_type, relaxation_time, 
                                      selfcare_frequency, relaxation_tools, 
                                      has_previous_mental_health_app_experience,
                                      therapy_chat_history_preference, country, gender,
                                      created_at, updated_at)
        VALUES (:profile_id, :user_id, 'INTJ', 'Evening', 'Once a day', 
                ARRAY['Meditation', 'Deep breathing', 'Walking'], true, 'Keep history', 
                'United States', 'Male', NOW(), NOW())
    """), {'profile_id': str(uuid.uuid4()), 'user_id': user_id})
    
    # Example agent personality
    connection.execute(sa.text("""
        INSERT INTO agent_personality (id, user_id, agent_style, communication_tone, 
                                      therapy_approach, mood_patterns, stress_triggers,
                                      coping_strategies, progress_areas, created_at, updated_at)
        VALUES (:personality_id, :user_id, 'Supportive', 'Friendly', 'CBT',
                'Generally positive with occasional stress', 'Work deadlines, social situations',
                'Breathing exercises, positive self-talk', 'Stress management, emotional awareness',
                NOW(), NOW())
    """), {'personality_id': str(uuid.uuid4()), 'user_id': user_id})
    
    # Example breathing patterns
    connection.execute(sa.text("""
        INSERT INTO breathing_patterns (id, user_id, name, inhale_seconds, hold_seconds, 
                                      exhale_seconds, cycles, rest_seconds, 
                                      description, is_preset, is_active, processed_for_tags,
                                      created_at, updated_at)
        VALUES 
        (:pattern1_id, NULL, '4-7-8 Breathing', 4, 7, 8, 4, 0, 'Calming breathing technique', true, true, false, NOW(), NOW()),
        (:pattern2_id, NULL, 'Box Breathing', 4, 4, 4, 4, 4, 'Balanced breathing pattern', true, true, false, NOW(), NOW()),
        (:pattern3_id, NULL, 'Deep Breathing', 6, 0, 6, 6, 0, 'Simple deep breathing exercise', true, true, false, NOW(), NOW())
    """), {
        'pattern1_id': str(uuid.uuid4()),
        'pattern2_id': str(uuid.uuid4()),
        'pattern3_id': str(uuid.uuid4())
    })
    
    # Example custom emotions
    connection.execute(sa.text("""
        INSERT INTO custom_emotions (id, user_id, name, color, description, is_active, 
                                   processed_for_tags, usage_count, created_at, updated_at)
        VALUES 
        (:emotion1_id, :user_id, 'Content', 4280391, 'Feeling satisfied and peaceful', true, false, 0, NOW(), NOW()),
        (:emotion2_id, :user_id, 'Motivated', 4283214, 'Feeling driven and energetic', true, false, 0, NOW(), NOW())
    """), {
        'emotion1_id': str(uuid.uuid4()),
        'emotion2_id': str(uuid.uuid4()),
        'user_id': user_id
    })
    
    # Example tag semantics
    connection.execute(sa.text("""
        INSERT INTO tag_semantics (id, tag, category, similar_tags, synonyms, usage_count, unique_users,
                                  first_seen, last_updated)
        VALUES 
        (:tag1_id, 'stress', 'emotional', '{"anxiety": 0.8, "tension": 0.7}', '["pressure", "strain"]', 1, 1, NOW(), NOW()),
        (:tag2_id, 'calm', 'emotional', '{"peaceful": 0.9, "relaxed": 0.8}', '["serene", "tranquil"]', 1, 1, NOW(), NOW()),
        (:tag3_id, 'work', 'contextual', '{"job": 0.9, "career": 0.8}', '["employment", "occupation"]', 1, 1, NOW(), NOW())
    """), {
        'tag1_id': str(uuid.uuid4()),
        'tag2_id': str(uuid.uuid4()),
        'tag3_id': str(uuid.uuid4())
    })
    
    # Example user profile (analytics)
    connection.execute(sa.text("""
        INSERT INTO user_profiles (id, user_id, frequent_tags, tag_categories, tag_trends,
                                  personality_insights, behavioral_patterns, preferences,
                                  total_interactions, unique_tags_count, created_at, updated_at)
        VALUES (:profile_id, :user_id, 
                '{"stress": 5, "calm": 3, "work": 2}', 
                '{"emotional": ["stress", "calm"], "contextual": ["work"]}',
                '{"stress": {"trend": "decreasing", "frequency": "weekly"}}',
                '{"personality": "INTJ", "stress_response": "analytical"}',
                '{"breathing_sessions": "evening", "emotion_tracking": "daily"}',
                '{"preferred_topics": ["stress_management", "breathing_exercises"]}',
                10, 3, NOW(), NOW())
    """), {'profile_id': str(uuid.uuid4()), 'user_id': user_id})
    
    # Example token usage
    connection.execute(sa.text("""
        INSERT INTO token_usage (id, user_id, interaction_type, model, data_id,
                                tokens_total, tokens_prompt, tokens_completion, created_at)
        VALUES (:usage_id, :user_id, 'chat', 'gpt-4', :conversation_id,
                150, 50, 100, NOW())
    """), {
        'usage_id': str(uuid.uuid4()),
        'user_id': user_id,
        'conversation_id': str(uuid.uuid4())
    })


def downgrade() -> None:
    """Drop all tables"""
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('token_usage')
    op.drop_table('tag_semantics')
    op.drop_table('user_profiles')
    op.drop_table('custom_emotions')
    op.drop_table('breathing_patterns')
    op.drop_table('breathing_sessions')
    op.drop_table('emotional_records')
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('agent_personality')
    op.drop_table('user_profile_data')
    op.drop_table('users')
