# Database Setup Guide for EmotionAI API

This guide covers setting up PostgreSQL RDS and creating the database schema for your EmotionAI API.

## 🎯 **Overview**

- **Database**: PostgreSQL 15+ on AWS RDS
- **Schema Management**: SQLAlchemy + Alembic migrations
- **Instance**: db.t3.micro (free tier eligible)

---

## 📋 **Pre-requisites**

1. AWS RDS PostgreSQL instance running
2. Security groups configured for database access
3. EmotionAI API code deployed on EC2

---

## 🚀 **Database Setup Steps**

### **1. Connect to RDS Instance**

First, test your connection to RDS:

```bash
# Test connection from EC2 instance
psql -h your-rds-endpoint.region.rds.amazonaws.com -U emotionai_user -d emotionai_prod

# If connection works, you should see:
# emotionai_prod=>
```

### **2. Set Environment Variables**

Ensure your `.env` file has the correct RDS connection string:

```bash
# Update your .env file
DATABASE_URL=postgresql://emotionai_user:YOUR_PASSWORD@your-rds-endpoint.region.rds.amazonaws.com:5432/emotionai_prod
```

### **3. Install Database Tools**

```bash
# On your EC2 instance
sudo apt update
sudo apt install -y postgresql-client-15

# Activate your Python virtual environment
cd /opt/emotionai-api
source venv/bin/activate

# Install Python database packages
pip install alembic psycopg2-binary asyncpg
```

### **4. Create Database Schema**

You have two options:

#### **Option A: Direct Schema Creation (Quick)**

```bash
# Create all tables directly
python create_schema.py create

# Verify tables were created
python create_schema.py info
```

#### **Option B: Using Migrations (Recommended)**

```bash
# Initialize Alembic migrations
python manage_db.py init

# Create initial migration
python manage_db.py new-migration --message "Initial schema"

# Apply migrations
python manage_db.py migrate

# Check migration status
python manage_db.py status
```

### **5. Verify Database Setup**

```bash
# Show database information
python manage_db.py info

# Test API connection to database
curl http://localhost:8000/health/detailed
```

---

## 📊 **Database Schema Overview**

Your EmotionAI database includes the following tables:

### **Core Tables**

1. **`users`** - User accounts and profiles
   - id (UUID, Primary Key)
   - email (Unique, Indexed)
   - hashed_password
   - first_name, last_name
   - agent_personality_data (JSON)
   - user_profile_data (JSON)
   - Timestamps: created_at, updated_at, last_login_at

2. **`conversations`** - AI agent conversations
   - id (UUID, Primary Key)
   - user_id (Foreign Key → users.id)
   - agent_type (therapy, wellness)
   - title, context_data (JSON)
   - Timestamps: created_at, updated_at, last_message_at

3. **`messages`** - Individual conversation messages
   - id (UUID, Primary Key)
   - conversation_id (Foreign Key → conversations.id)
   - content (Text)
   - role (user/assistant)
   - metadata (JSON)
   - Crisis detection fields: crisis_detected, crisis_severity

4. **`emotional_records`** - User emotion tracking
   - id (UUID, Primary Key)
   - user_id (Foreign Key → users.id)
   - emotion, intensity (1-10)
   - triggers (JSON), notes
   - Timestamps: recorded_at, created_at

5. **`breathing_sessions`** - Breathing exercise data
   - id (UUID, Primary Key)
   - user_id (Foreign Key → users.id)
   - pattern_name, duration_minutes
   - effectiveness_rating (1-5)
   - session_data (JSON)
   - Timestamps: started_at, completed_at

6. **`domain_events`** - Event sourcing
   - id (UUID, Primary Key)
   - event_type, event_data (JSON)
   - Processing status and retry logic

### **Indexes**

- `idx_users_email` - Fast user lookup by email
- `idx_users_active` - Filter active users
- `idx_users_created_at` - User registration timeline
- Plus foreign key indexes for relationships

---

## 🔧 **Database Management Commands**

### **Schema Management**

```bash
# Show current database status
python manage_db.py info

# Create new migration after model changes
python manage_db.py new-migration --message "Add new feature"

# Apply pending migrations
python manage_db.py migrate

# Rollback last migration
python manage_db.py rollback

# Rollback multiple migrations
python manage_db.py rollback --steps 3
```

### **Backup & Restore**

```bash
# Create database backup
python manage_db.py backup

# Restore from backup
python manage_db.py restore --file backup_emotionai_20240101_120000.sql
```

### **Troubleshooting**

```bash
# Check migration status
python manage_db.py status

# Show detailed database information
python create_schema.py info

# Test database connection
python -c "
import asyncio
from src.infrastructure.config.settings import settings
from src.infrastructure.database.connection import DatabaseConnection

async def test():
    db = await DatabaseConnection.create(settings)
    print('✅ Database connection successful!')
    await db.close()

asyncio.run(test())
"
```

---

## 🛡️ **Security Considerations**

### **1. Connection Security**

```bash
# Always use SSL in production
# Your DATABASE_URL should include sslmode:
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

### **2. User Permissions**

```sql
-- Connect as admin user to RDS
-- Grant only necessary permissions to app user
GRANT CONNECT ON DATABASE emotionai_prod TO emotionai_user;
GRANT USAGE ON SCHEMA public TO emotionai_user;
GRANT CREATE ON SCHEMA public TO emotionai_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO emotionai_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO emotionai_user;

-- For future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO emotionai_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO emotionai_user;
```

### **3. Backup Security**

```bash
# Encrypt backups
gpg --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 \
    --s2k-digest-algo SHA512 --s2k-count 65536 --symmetric \
    --output backup_encrypted.sql.gpg backup_emotionai.sql

# Decrypt backup
gpg --decrypt backup_encrypted.sql.gpg > backup_restored.sql
```

---

## 📈 **Performance Optimization**

### **1. Connection Pooling**

```bash
# In your .env file
DATABASE_POOL_SIZE=5          # Conservative for t2.micro
DATABASE_MAX_OVERFLOW=10      # Allow some overflow
```

### **2. Query Optimization**

```sql
-- Monitor slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check index usage
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE schemaname = 'public';
```

### **3. Maintenance**

```bash
# Setup automated maintenance (add to crontab)
# Daily VACUUM at 3 AM
0 3 * * * PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "VACUUM ANALYZE;"

# Weekly REINDEX on Sunday
0 2 * * 0 PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "REINDEX DATABASE emotionai_prod;"
```

---

## 🚨 **Common Issues & Solutions**

### **1. Connection Timeouts**

```bash
# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxxxxxxx

# Test network connectivity
telnet your-rds-endpoint.region.rds.amazonaws.com 5432
```

### **2. Permission Denied**

```sql
-- Check user permissions
\du emotionai_user

-- Fix common permission issues
GRANT ALL PRIVILEGES ON DATABASE emotionai_prod TO emotionai_user;
```

### **3. Migration Conflicts**

```bash
# Check migration status
python manage_db.py status

# Reset to specific migration
alembic downgrade revision_id
alembic upgrade head
```

### **4. Schema Drift**

```bash
# Compare database with models
python manage_db.py new-migration --message "Fix schema drift"

# This will show any differences between your models and database
```

---

## 📚 **Migration Best Practices**

### **1. Always Review Migrations**

```bash
# After creating a migration
cat migrations/versions/latest_migration.py

# Test on development first
python manage_db.py migrate  # On dev environment
```

### **2. Backup Before Major Changes**

```bash
# Before running migrations in production
python manage_db.py backup
python manage_db.py migrate
```

### **3. Zero-Downtime Migrations**

```python
# For production deployments:
# 1. Add new columns as nullable first
# 2. Deploy code that handles both old and new schema
# 3. Migrate data
# 4. Make columns non-nullable if needed
# 5. Remove old columns in next release
```

---

## ✅ **Verification Checklist**

After setting up your database:

- [ ] RDS instance is running and accessible
- [ ] Security groups allow connection from EC2
- [ ] Database user has correct permissions
- [ ] All tables created successfully
- [ ] Indexes are present and functional
- [ ] API can connect to database
- [ ] Health check endpoint returns database status
- [ ] Backup strategy is in place
- [ ] Monitoring is configured

---

Your EmotionAI database is now ready for production! 🎉

For ongoing maintenance, use the `manage_db.py` script for all database operations.