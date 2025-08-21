# Therapy Agent Context Database Check

This document provides database queries to verify that the therapy chat is properly storing context and conversation data for users.

## Prerequisites

Make sure you have access to the PostgreSQL database container:

```bash
docker-compose exec db psql -U emotionai -d emotionai_db
```

## 1. Check User by Email

First, find a user by their email address:

```sql
-- Find user by email
SELECT 
    id,
    email,
    username,
    first_name,
    last_name,
    created_at,
    last_login_at
FROM users 
WHERE email = 'user@example.com';  -- Replace with actual email
```

## 2. Check User's Therapy Conversations

Check if the user has any therapy conversations:

```sql
-- Get all therapy conversations for a specific user
SELECT 
    c.id as conversation_id,
    c.title,
    c.agent_type,
    c.is_active,
    c.message_count,
    c.created_at,
    c.last_message_at,
    c.context_data
FROM conversations c
JOIN users u ON c.user_id = u.id
WHERE u.email = 'john.doe@example.com'
  AND c.agent_type = 'therapy'
ORDER BY c.last_message_at DESC;
```

## 3. Check Conversation Messages

Check the actual messages in a specific conversation:

```sql
-- Get all messages from a specific conversation
SELECT 
    m.id as message_id,
    m.content,
    m.message_type,
    m.timestamp,
    m.message_metadata,
    m.tags,
    m.tag_confidence
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
JOIN users u ON c.user_id = u.id
WHERE u.id = '550e8400-e29b-41d4-a716-446655440000' 
  AND c.agent_type = 'therapy'
  AND c.id = '08c17e04-acdc-426c-91fd-a7ddfe393073'
ORDER BY m.timestamp ASC;
```

## 4. Check User Profile Data

Check if the user has profile data that might be used for context:

```sql
-- Get user profile data
SELECT 
    up.id,
    up.personality_type,
    up.relaxation_time,
    up.selfcare_frequency,
    up.relaxation_tools,
    up.has_previous_mental_health_app_experience,
    up.therapy_chat_history_preference,
    up.country,
    up.gender,
    up.created_at,
    up.updated_at
FROM user_profile_data up
JOIN users u ON up.user_id = u.id
WHERE u.email = 'user@example.com';  -- Replace with actual email
```

## 5. Check Agent Personality Data

Check if the user has agent personality data:

```sql
-- Get agent personality data
SELECT 
    ap.id,
    ap.therapy_approach,
    ap.communication_style,
    ap.empathy_level,
    ap.specialization_areas,
    ap.adaptation_preferences,
    ap.created_at,
    ap.updated_at
FROM agent_personality ap
JOIN users u ON ap.user_id = u.id
WHERE u.email = 'user@example.com';  -- Replace with actual email
```

## 6. Check Emotional Records

Check if the user has emotional records that might be used for context:

```sql
-- Get recent emotional records
SELECT 
    er.id,
    er.emotion,
    er.intensity,
    er.triggers,
    er.notes,
    er.context_data,
    er.tags,
    er.recorded_at,
    er.created_at
FROM emotional_records er
JOIN users u ON er.user_id = u.id
WHERE u.email = 'user@example.com'  -- Replace with actual email
ORDER BY er.recorded_at DESC
LIMIT 10;
```

## 7. Comprehensive User Context Check

Get a complete overview of a user's therapy context:

```sql
-- Comprehensive user therapy context
WITH user_info AS (
    SELECT id, email, username, first_name, last_name
    FROM users 
    WHERE id = '550e8400-e29b-41d4-a716-446655440000'
),
conversation_summary AS (
    SELECT 
        c.id as conversation_id,
        c.title,
        c.agent_type,
        c.is_active,
        c.message_count,
        c.created_at,
        c.last_message_at,
        COUNT(m.id) as actual_message_count
    FROM conversations c
    LEFT JOIN messages m ON c.id = m.conversation_id
    JOIN user_info u ON c.user_id = u.id
    WHERE c.agent_type = 'therapy'
    GROUP BY c.id, c.title, c.agent_type, c.is_active, c.message_count, c.created_at, c.last_message_at
)
SELECT 
    u.email,
    u.username,
    u.first_name,
    u.last_name,
    cs.conversation_id,
    cs.title,
    cs.agent_type,
    cs.is_active,
    cs.message_count as stored_message_count,
    cs.actual_message_count,
    cs.created_at,
    cs.last_message_at,
    CASE 
        WHEN cs.message_count != cs.actual_message_count THEN 'MISMATCH'
        ELSE 'OK'
    END as message_count_status
FROM user_info u
LEFT JOIN conversation_summary cs ON true
ORDER BY cs.last_message_at DESC NULLS LAST;
```

## 8. Check for Active Therapy Sessions

Find users with active therapy sessions:

```sql
-- Find users with active therapy sessions
SELECT 
    u.email,
    u.username,
    c.id as conversation_id,
    c.title,
    c.message_count,
    c.last_message_at,
    EXTRACT(EPOCH FROM (NOW() - c.last_message_at))/60 as minutes_since_last_message
FROM users u
JOIN conversations c ON u.id = c.user_id
WHERE c.agent_type = 'therapy'
  AND c.is_active = true
ORDER BY c.last_message_at DESC;
```

## 9. Check Message Metadata

Examine the metadata stored with messages to understand context:

```sql
-- Check message metadata for context
SELECT 
    m.id as message_id,
    m.content,
    m.message_type,
    m.message_metadata,
    m.tags,
    m.timestamp,
    c.title as conversation_title
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
JOIN users u ON c.user_id = u.id
WHERE u.id = '550e8400-e29b-41d4-a716-446655440000' 
  AND c.agent_type = 'therapy'
  AND m.message_metadata IS NOT NULL
ORDER BY m.timestamp DESC
LIMIT 20;
```

## 10. Check Database Schema

Verify the database schema is correct:

```sql
-- Check table structure
\d conversations
\d messages
\d user_profile_data
\d agent_personality
\d emotional_records
```

## 11. Check Indexes

Verify that proper indexes exist for performance:

```sql
-- Check indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('conversations', 'messages', 'user_profile_data', 'agent_personality')
ORDER BY tablename, indexname;
```

## 12. Check Recent Activity

Get recent therapy activity across all users:

```sql
-- Recent therapy activity
SELECT 
    u.email,
    c.title,
    c.message_count,
    c.last_message_at,
    m.content as last_message_preview
FROM conversations c
JOIN users u ON c.user_id = u.id
LEFT JOIN LATERAL (
    SELECT content 
    FROM messages 
    WHERE conversation_id = c.id 
    ORDER BY timestamp DESC 
    LIMIT 1
) m ON true
WHERE c.agent_type = 'therapy'
  AND c.last_message_at > NOW() - INTERVAL '24 hours'
ORDER BY c.last_message_at DESC;
```

## Troubleshooting Common Issues

### Issue: No conversations found
- Check if the user exists in the `users` table
- Verify the email address is correct
- Check if any conversations were created

### Issue: Message count mismatch
- The `message_count` field might not be updated properly
- Check if the `_get_message_count` method is working

### Issue: No profile data
- Check if the user has completed the profile setup
- Verify the `user_profile_data` table exists and has data

### Issue: No emotional records
- Check if emotional tracking is enabled
- Verify the `emotional_records` table exists

## Expected Results

For a user who has used the therapy chat, you should see:

1. **At least one conversation** in the `conversations` table with `agent_type = 'therapy'`
2. **Multiple messages** in the `messages` table for that conversation
3. **User profile data** if the user has completed their profile
4. **Agent personality data** if the system has learned user preferences
5. **Emotional records** if the user has tracked emotions

## Notes

- Replace `'user@example.com'` with the actual email address you want to check
- The `conversation_id` in queries should be replaced with actual UUID values
- Some queries might return empty results if the user hasn't used the therapy features yet
- Check the API logs for any errors during conversation creation or message storage
