-- Complete Database Setup Script for EmotionAI API
-- This script creates all tables and inserts test data for immediate testing

-- Enable UUID extension (if available)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table with all required columns
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100),
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_verified BOOLEAN NOT NULL DEFAULT false,
    agent_personality_data JSONB,
    user_profile_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_login_at TIMESTAMP WITH TIME ZONE
);

-- Create conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    agent_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    context_data JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    message_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    message_type VARCHAR(20) NOT NULL,
    message_metadata JSONB,
    tags JSONB,
    tag_confidence FLOAT,
    processed_for_tags BOOLEAN NOT NULL DEFAULT false,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create token_usage table
CREATE TABLE IF NOT EXISTS token_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    interaction_type VARCHAR(50) NOT NULL,
    model VARCHAR(100),
    data_id VARCHAR(100),
    tokens_total INTEGER NOT NULL,
    tokens_prompt INTEGER NOT NULL DEFAULT 0,
    tokens_completion INTEGER NOT NULL DEFAULT 0,
    usage_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create breathing_patterns table
CREATE TABLE IF NOT EXISTS breathing_patterns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    name VARCHAR(100) NOT NULL,
    inhale_seconds INTEGER NOT NULL,
    hold_seconds INTEGER NOT NULL,
    exhale_seconds INTEGER NOT NULL,
    cycles INTEGER NOT NULL,
    rest_seconds INTEGER NOT NULL,
    description TEXT,
    is_preset BOOLEAN NOT NULL,
    is_active BOOLEAN NOT NULL,
    tags JSONB,
    tag_confidence FLOAT,
    processed_for_tags BOOLEAN NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create custom_emotions table
CREATE TABLE IF NOT EXISTS custom_emotions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    name VARCHAR(50) NOT NULL,
    color BIGINT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL,
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMP WITH TIME ZONE,
    tags JSONB,
    tag_confidence FLOAT,
    processed_for_tags BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    UNIQUE(user_id, name)
);

-- Create emotional_records table
CREATE TABLE IF NOT EXISTS emotional_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id),
    standard_emotion VARCHAR(50),
    custom_emotion_id UUID REFERENCES custom_emotions(id),
    custom_emotion_color BIGINT,
    intensity INTEGER NOT NULL,
    notes TEXT,
    tags JSONB,
    tag_confidence FLOAT,
    processed_for_tags BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create basic indexes for better performance (without GIN)
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_conversations_user_agent ON conversations(user_id, agent_type);
CREATE INDEX IF NOT EXISTS idx_conversations_active ON conversations(is_active);
CREATE INDEX IF NOT EXISTS idx_conversations_last_message ON conversations(last_message_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(message_type);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_token_usage_user_created ON token_usage(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_token_usage_type ON token_usage(interaction_type);
CREATE INDEX IF NOT EXISTS idx_breathing_patterns_user ON breathing_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_breathing_patterns_preset ON breathing_patterns(is_preset);
CREATE INDEX IF NOT EXISTS idx_breathing_patterns_name ON breathing_patterns(name);
CREATE INDEX IF NOT EXISTS idx_custom_emotions_user ON custom_emotions(user_id);
CREATE INDEX IF NOT EXISTS idx_custom_emotions_name ON custom_emotions(name);
CREATE INDEX IF NOT EXISTS idx_emotional_records_user ON emotional_records(user_id);
CREATE INDEX IF NOT EXISTS idx_emotional_records_created ON emotional_records(created_at);

-- Insert test data

-- Test User 1
INSERT INTO users (id, email, username, hashed_password, first_name, last_name, is_active, is_verified) VALUES
('550e8400-e29b-41d4-a716-446655440000', 'test@example.com', 'testuser', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4tbQJxqKre', 'Test', 'User', true, true);

-- Test User 2
INSERT INTO users (id, email, username, hashed_password, first_name, last_name, is_active, is_verified) VALUES
('550e8400-e29b-41d4-a716-446655440001', 'demo@example.com', 'demouser', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4tbQJxqKre', 'Demo', 'User', true, true);

-- Test Conversation
INSERT INTO conversations (id, user_id, agent_type, title, context_data, is_active, message_count) VALUES
('550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'therapy', 'First Therapy Session', '{"mood": "anxious", "focus": "stress management"}', true, 2);

-- Test Messages
INSERT INTO messages (id, conversation_id, user_id, content, message_type, message_metadata) VALUES
('550e8400-e29b-41d4-a716-446655440003', '550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'I have been feeling very stressed lately', 'user', '{"tokens": 15}'),
('550e8400-e29b-41d4-a716-446655440004', '550e8400-e29b-41d4-a716-446655440002', '550e8400-e29b-41d4-a716-446655440000', 'I understand you are feeling stressed. Let me help you with some breathing exercises.', 'assistant', '{"tokens": 25}');

-- Test Token Usage
INSERT INTO token_usage (id, user_id, interaction_type, model, tokens_total, tokens_prompt, tokens_completion, usage_metadata) VALUES
('550e8400-e29b-41d4-a716-446655440005', '550e8400-e29b-41d4-a716-446655440000', 'chat', 'gpt-4', 40, 15, 25, '{"session_id": "test_session_1"}');

-- Default Breathing Patterns
INSERT INTO breathing_patterns (id, user_id, name, inhale_seconds, hold_seconds, exhale_seconds, cycles, rest_seconds, description, is_preset, is_active, processed_for_tags) VALUES
('550e8400-e29b-41d4-a716-446655440006', NULL, '4-7-8 Relaxation Breath', 4, 7, 8, 4, 2, 'Classic relaxation breathing pattern', true, true, false),
('550e8400-e29b-41d4-a716-446655440007', NULL, 'Box Breathing', 4, 4, 4, 4, 4, 'Equal breathing for focus and calm', true, true, false),
('550e8400-e29b-41d4-a716-446655440008', NULL, 'Calm Breath', 3, 0, 6, 5, 1, 'Simple calming breath', true, true, false),
('550e8400-e29b-41d4-a716-446655440009', NULL, 'Wim Hof Method', 2, 0, 2, 30, 0, 'Energizing breathing technique', true, true, false),
('550e8400-e29b-41d4-a716-446655440010', NULL, 'Deep Yoga Breath', 5, 2, 5, 10, 1, 'Deep yogic breathing', true, true, false);

-- Test Custom Emotions (using smaller color values)
INSERT INTO custom_emotions (id, user_id, name, color, description, is_active, usage_count) VALUES
('550e8400-e29b-41d4-a716-446655440011', '550e8400-e29b-41d4-a716-446655440000', 'Calm Joy', 16711680, 'A peaceful, content feeling', true, 3),
('550e8400-e29b-41d4-a716-446655440012', '550e8400-e29b-41d4-a716-446655440000', 'Productive Energy', 65280, 'Motivated and focused', true, 5);

-- Test Emotional Records
INSERT INTO emotional_records (id, user_id, standard_emotion, custom_emotion_id, custom_emotion_color, intensity, notes, created_at) VALUES
('550e8400-e29b-41d4-a716-446655440013', '550e8400-e29b-41d4-a716-446655440000', 'happy', NULL, NULL, 7, 'Feeling good today', NOW() - INTERVAL '2 hours'),
('550e8400-e29b-41d4-a716-446655440014', '550e8400-e29b-41d4-a716-446655440000', NULL, '550e8400-e29b-41d4-a716-446655440011', 16711680, 8, 'Very calm and peaceful', NOW() - INTERVAL '1 hour');

-- Update conversation message count
UPDATE conversations SET message_count = 2 WHERE id = '550e8400-e29b-41d4-a716-446655440002';

-- Display created tables
\dt

-- Display sample data
SELECT 'Users:' as info;
SELECT id, email, username, first_name, last_name FROM users;

SELECT 'Conversations:' as info;
SELECT id, user_id, agent_type, title, message_count FROM conversations;

SELECT 'Messages:' as info;
SELECT id, conversation_id, message_type, LEFT(content, 50) as content_preview FROM messages;

SELECT 'Breathing Patterns:' as info;
SELECT id, name, inhale_seconds, hold_seconds, exhale_seconds, cycles FROM breathing_patterns;

SELECT 'Custom Emotions:' as info;
SELECT id, user_id, name, color, usage_count FROM custom_emotions;

SELECT 'Emotional Records:' as info;
SELECT id, user_id, standard_emotion, custom_emotion_id, intensity, created_at FROM emotional_records;
