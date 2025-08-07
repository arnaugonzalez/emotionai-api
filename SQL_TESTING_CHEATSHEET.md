# 🐳 EmotionAI Database SQL Testing Cheatsheet

## 🔌 **Connect to Database**
```bash
# Connect to PostgreSQL in Docker
docker exec -it emotionai-api-db-1 psql -U emotionai -d emotionai_db
```

## 📊 **Basic Database Commands**
```sql
-- List all tables
\dt

-- Describe table structure
\d users
\d emotional_records
\d breathing_sessions
\d tag_semantics

-- List all databases
\l

-- Show current database
SELECT current_database();

-- Quit psql
\q
```

## 👤 **User Management Queries**

### Check Test User
```sql
-- Verify test user exists
SELECT email, is_active, created_at, hashed_password 
FROM users 
WHERE email = 'test@emotionai.com';

-- Count total users
SELECT COUNT(*) as total_users FROM users;

-- List all users
SELECT id, email, is_active, created_at FROM users ORDER BY created_at DESC;
```

### User Profile Queries
```sql
-- Check user with profile data
SELECT 
    u.email, 
    up.name, 
    up.age, 
    up.country, 
    up.personality_type
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id;

-- Check profile completeness
SELECT 
    u.email,
    CASE 
        WHEN up.name IS NOT NULL THEN 'Complete'
        ELSE 'Incomplete'
    END as profile_status
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id;
```

## 🧠 **Emotional Records Queries**

### Recent Emotional Records
```sql
-- Last 10 emotional records
SELECT 
    er.emotion, 
    er.intensity, 
    er.notes, 
    er.created_at,
    u.email
FROM emotional_records er
JOIN users u ON er.user_id = u.id
ORDER BY er.created_at DESC 
LIMIT 10;

-- Emotion statistics
SELECT 
    emotion, 
    AVG(intensity) as avg_intensity,
    COUNT(*) as count
FROM emotional_records
GROUP BY emotion
ORDER BY count DESC;

-- Records by user
SELECT 
    u.email,
    COUNT(er.id) as total_records,
    AVG(er.intensity) as avg_intensity
FROM users u
LEFT JOIN emotional_records er ON u.id = er.user_id
GROUP BY u.id, u.email;
```

### Tag Analysis
```sql
-- Records with tags
SELECT 
    er.emotion,
    er.tags,
    er.tag_confidence,
    er.processed_for_tags
FROM emotional_records er
WHERE er.tags IS NOT NULL
ORDER BY er.created_at DESC;
```

## 🫁 **Breathing Sessions Queries**

### Session Statistics
```sql
-- Recent breathing sessions
SELECT 
    bs.pattern_name,
    bs.duration_minutes,
    bs.completed,
    bs.effectiveness_rating,
    bs.started_at,
    u.email
FROM breathing_sessions bs
JOIN users u ON bs.user_id = u.id
ORDER BY bs.started_at DESC
LIMIT 10;

-- Pattern popularity
SELECT 
    pattern_name,
    COUNT(*) as session_count,
    AVG(duration_minutes) as avg_duration,
    AVG(effectiveness_rating) as avg_rating
FROM breathing_sessions
WHERE completed = true
GROUP BY pattern_name
ORDER BY session_count DESC;

-- Completion rates
SELECT 
    pattern_name,
    COUNT(*) as total_sessions,
    SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed_sessions,
    ROUND(
        (SUM(CASE WHEN completed THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2
    ) as completion_rate
FROM breathing_sessions
GROUP BY pattern_name
ORDER BY completion_rate DESC;
```

## 🏷️ **Tag Semantics Queries**

### Tag Analysis
```sql
-- Most used tags
SELECT tag, category, usage_count, unique_users
FROM tag_semantics
ORDER BY usage_count DESC
LIMIT 20;

-- Tags by category
SELECT 
    category,
    COUNT(*) as tag_count,
    SUM(usage_count) as total_usage
FROM tag_semantics
GROUP BY category
ORDER BY total_usage DESC;

-- Similar tags for stress
SELECT 
    tag,
    similar_tags,
    synonyms
FROM tag_semantics
WHERE tag LIKE '%stress%' OR synonyms::text LIKE '%stress%';
```

## 🔍 **Advanced Testing Queries**

### User Activity Summary
```sql
-- Complete user activity overview
SELECT 
    u.email,
    u.created_at as user_since,
    COUNT(DISTINCT er.id) as emotion_records,
    COUNT(DISTINCT bs.id) as breathing_sessions,
    COUNT(DISTINCT CASE WHEN bs.completed THEN bs.id END) as completed_sessions,
    AVG(er.intensity) as avg_emotion_intensity,
    AVG(bs.effectiveness_rating) as avg_session_rating
FROM users u
LEFT JOIN emotional_records er ON u.id = er.user_id
LEFT JOIN breathing_sessions bs ON u.id = bs.user_id
GROUP BY u.id, u.email, u.created_at
ORDER BY u.created_at DESC;
```

### Data Quality Checks
```sql
-- Check for orphaned records
SELECT 'emotional_records' as table_name, COUNT(*) as orphaned_count
FROM emotional_records er
LEFT JOIN users u ON er.user_id = u.id
WHERE u.id IS NULL

UNION ALL

SELECT 'breathing_sessions' as table_name, COUNT(*) as orphaned_count
FROM breathing_sessions bs
LEFT JOIN users u ON bs.user_id = u.id
WHERE u.id IS NULL;

-- Check data ranges
SELECT 
    'emotional_records' as table_name,
    MIN(intensity) as min_intensity,
    MAX(intensity) as max_intensity,
    COUNT(*) as total_records
FROM emotional_records

UNION ALL

SELECT 
    'breathing_sessions' as table_name,
    MIN(duration_minutes) as min_duration,
    MAX(duration_minutes) as max_duration,
    COUNT(*) as total_sessions
FROM breathing_sessions;
```

## 🛠️ **Maintenance & Testing Queries**

### Reset Test Data
```sql
-- Reset test user password (use actual bcrypt hash)
UPDATE users 
SET hashed_password = '$2b$12$your_actual_bcrypt_hash_here'
WHERE email = 'test@emotionai.com';

-- Activate test user
UPDATE users 
SET is_active = true 
WHERE email = 'test@emotionai.com';

-- Add sample emotional record for testing
INSERT INTO emotional_records (user_id, emotion, intensity, notes, created_at)
SELECT 
    u.id, 
    'happy', 
    8, 
    'Test record for login verification',
    NOW()
FROM users u 
WHERE u.email = 'test@emotionai.com';
```

### Database Cleanup
```sql
-- Remove old test records (older than 7 days)
DELETE FROM emotional_records 
WHERE created_at < NOW() - INTERVAL '7 days' 
AND notes LIKE '%test%';

-- Vacuum database for performance
VACUUM ANALYZE;

-- Check database size
SELECT 
    pg_size_pretty(pg_database_size('emotionai_db')) as database_size;
```

## 🚀 **Quick Login Test Verification**

```sql
-- Comprehensive test user check
SELECT 
    u.email,
    u.is_active,
    u.hashed_password IS NOT NULL as has_password,
    u.created_at,
    up.name as profile_name,
    COUNT(er.id) as emotion_records,
    COUNT(bs.id) as breathing_sessions
FROM users u
LEFT JOIN user_profiles up ON u.id = up.user_id
LEFT JOIN emotional_records er ON u.id = er.user_id
LEFT JOIN breathing_sessions bs ON u.id = bs.user_id
WHERE u.email = 'test@emotionai.com'
GROUP BY u.id, u.email, u.is_active, u.hashed_password, u.created_at, up.name;
```

## 📋 **Common Issues & Solutions**

### Issue: User Not Found
```sql
-- Check if user exists at all
SELECT COUNT(*) FROM users WHERE email = 'test@emotionai.com';

-- If 0, run the test data script:
-- docker exec -it emotionai-api-api-1 python create_test_data.py
```

### Issue: User Inactive
```sql
-- Activate user
UPDATE users SET is_active = true WHERE email = 'test@emotionai.com';
```

### Issue: Password Problems
```sql
-- Check password hash format
SELECT 
    email, 
    LENGTH(hashed_password) as hash_length,
    LEFT(hashed_password, 10) as hash_start
FROM users 
WHERE email = 'test@emotionai.com';

-- Should show: hash_length = 60, hash_start = '$2b$12$...'
```

---

## 💡 **Pro Tips**

- **Always backup before making changes**: `pg_dump -U emotionai emotionai_db > backup.sql`
- **Use transactions for testing**: `BEGIN; ... ROLLBACK;` to test without permanent changes
- **Monitor query performance**: Add `EXPLAIN ANALYZE` before SELECT queries
- **Check logs while testing**: `docker logs -f emotionai-api-api-1` in another terminal