# Fresh Database Start Guide

## Overview
This guide explains how to start fresh with a clean database and new Alembic migrations.

## What Was Done

### 1. Cleaned Up Old Migrations
- Deleted all existing migration files (001 through 006)
- Created a single new migration: `001_initial_schema.py`

### 2. New Migration Structure
The new migration `001_initial_schema.py` includes:

#### **Core Tables:**
- `users` - User accounts with all profile fields
- `user_profile_data` - Extended profile preferences (personality, relaxation tools, etc.)
- `agent_personality` - AI agent personality and therapy context

#### **Feature Tables:**
- `conversations` - Chat conversations with AI agents
- `messages` - Individual chat messages with intelligent tagging
- `emotional_records` - User emotional state tracking
- `breathing_sessions` - Breathing exercise sessions
- `breathing_patterns` - Breathing exercise patterns
- `custom_emotions` - User-defined emotional states

#### **Analytics Tables:**
- `user_profiles` - User behavior insights and tag analysis
- `tag_semantics` - Semantic relationships between tags
- `token_usage` - LLM token usage tracking
- `domain_events` - Event sourcing for system events

### 3. Example Data Included
The migration automatically creates:
- **Sample User**: John Doe (john.doe@example.com)
- **Profile Data**: INTJ personality, evening relaxation preference
- **Agent Personality**: Supportive style, CBT approach
- **Breathing Patterns**: 4-7-8, Box Breathing, Deep Breathing
- **Custom Emotions**: Content, Motivated
- **Tag Semantics**: stress, calm, work with relationships

## How to Use

### Step 1: Remove Docker Volume
```bash
# Stop containers
docker-compose down

# Remove the database volume
docker volume rm emotionai-api_postgres_data

# Or if using a different volume name, check with:
docker volume ls
```

### Step 2: Start Fresh
```bash
# Start containers (this will create a new empty database)
docker-compose up -d

# Wait for database to be ready (about 10-15 seconds)
sleep 15
```

### Step 3: Run the Migration
```bash
# Run the initial migration
docker-compose exec api alembic upgrade head
```

### Step 4: Verify
```bash
# Check migration status
docker-compose exec api alembic current

# Should show: 001_initial_schema
```

## Database Schema Benefits

### 1. **Normalized Structure**
- Profile data in dedicated tables instead of JSON columns
- Proper foreign key relationships
- Better data integrity and query performance

### 2. **Intelligent Tagging System**
- JSONB columns for semantic tag storage
- GIN indexes for fast tag-based searches
- Tag confidence scoring and relationships

### 3. **Comprehensive Coverage**
- All current models included
- Proper indexing for performance
- Example data for testing

### 4. **Future-Ready**
- Event sourcing infrastructure
- Token usage tracking
- Behavioral analytics support

## Testing the Setup

### 1. **Check Tables Exist**
```sql
\dt
-- Should show all 12 tables
```

### 2. **Verify Example Data**
```sql
SELECT * FROM users;
SELECT * FROM user_profile_data;
SELECT * FROM breathing_patterns;
```

### 3. **Test API Endpoints**
- Profile creation/retrieval should work
- No more "Unconsumed column names" errors
- New agent personality endpoints available

## Troubleshooting

### If Migration Fails
```bash
# Check logs
docker-compose logs api

# Reset and try again
docker-compose exec api alembic downgrade base
docker-compose exec api alembic upgrade head
```

### If Database Connection Issues
```bash
# Check if database is ready
docker-compose exec db pg_isready

# Check database logs
docker-compose logs db
```

## Next Steps

1. **Test Profile Creation**: Try creating a user profile through the API
2. **Test Agent Personality**: Use the new agent personality endpoints
3. **Verify Data Persistence**: Check that data is properly stored in the new tables
4. **Monitor Performance**: The new structure should be significantly faster

## Migration Rollback
If you need to rollback:
```bash
docker-compose exec api alembic downgrade base
```
This will drop all tables and return to a clean state.
