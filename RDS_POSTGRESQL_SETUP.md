# 🐘 RDS PostgreSQL Schema Setup for EmotionAI API

## 🎯 **Quick Answer**

To create your RDS PostgreSQL schema with the current code:

```bash
# 1. On your EC2 instance, after deployment
cd /opt/emotionai-api

# 2. Configure your .env with RDS connection
# DATABASE_URL=postgresql://emotionai_user:PASSWORD@your-rds-endpoint.region.rds.amazonaws.com:5432/emotionai_prod

# 3. Set up database schema
python3 create_schema.py create

# 4. Verify setup
python3 create_schema.py info
```

---

## 📋 **Complete Setup Process**

### **1. RDS PostgreSQL Instance Setup**

```bash
# Create RDS PostgreSQL instance via AWS CLI
aws rds create-db-instance \
    --db-instance-identifier emotionai-db \
    --db-instance-class db.t3.micro \
    --engine postgres \
    --engine-version 15.4 \
    --master-username emotionai_user \
    --master-user-password "YOUR_SECURE_PASSWORD" \
    --allocated-storage 20 \
    --storage-type gp2 \
    --vpc-security-group-ids sg-xxxxxxxx \
    --db-subnet-group-name your-subnet-group \
    --backup-retention-period 7 \
    --storage-encrypted \
    --no-multi-az \
    --no-publicly-accessible \
    --db-name emotionai_prod
```

**Or use AWS Console:**
1. Go to RDS → Create Database
2. Choose PostgreSQL 15+
3. Instance: db.t3.micro (free tier)
4. Database name: `emotionai_prod`
5. Username: `emotionai_user`
6. Set strong password
7. Configure security groups

### **2. Security Group Configuration**

```bash
# Create security group for RDS
aws ec2 create-security-group \
    --group-name emotionai-rds-sg \
    --description "EmotionAI RDS Security Group"

# Allow PostgreSQL from EC2 security group only
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG_ID
```

### **3. Environment Configuration**

Create/update your `.env` file on EC2:

```bash
# Database Configuration
DATABASE_URL=postgresql://emotionai_user:YOUR_PASSWORD@your-rds-endpoint.region.rds.amazonaws.com:5432/emotionai_prod
DATABASE_ECHO=false
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=10

# Other required variables...
SECRET_KEY=your-secret-key
OPENAI_API_KEY=your-openai-key
```

### **4. Database Schema Creation**

**Option A: Direct Schema Creation (Fastest)**

```bash
# Install dependencies
pip install psycopg2-binary asyncpg sqlalchemy

# Create all tables
python3 create_schema.py create

# Verify tables
python3 create_schema.py info
```

**Option B: Using Migrations (Production Recommended)**

```bash
# Install Alembic
pip install alembic

# Initialize migrations
python3 manage_db.py init

# Create initial migration
python3 manage_db.py new-migration --message "Initial schema"

# Apply migration
python3 manage_db.py migrate

# Check status
python3 manage_db.py status
```

### **5. Verification**

```bash
# Test database connection
python3 -c "
import asyncio, sys
sys.path.insert(0, 'src')
from src.infrastructure.config.settings import settings
from src.infrastructure.database.connection import DatabaseConnection

async def test():
    db = await DatabaseConnection.create(settings)
    print('✅ Connected successfully!')
    await db.close()

asyncio.run(test())
"

# Check API health with database
curl http://localhost:8000/health/detailed

# Show database schema
python3 manage_db.py info
```

---

## 🗃️ **Database Schema Details**

Your EmotionAI database will have these tables:

### **Core Tables Created:**

1. **`users`** - User accounts and profiles
2. **`conversations`** - AI chat conversations  
3. **`messages`** - Individual chat messages
4. **`emotional_records`** - Emotion tracking data
5. **`breathing_sessions`** - Breathing exercise sessions
6. **`domain_events`** - Event sourcing for analytics

### **Key Features:**

- **UUID Primary Keys** - Better for distributed systems
- **JSON Columns** - Flexible data storage for user profiles
- **Timestamps** - Created/updated tracking
- **Indexes** - Optimized for common queries
- **Foreign Key Constraints** - Data integrity
- **Crisis Detection Fields** - Mental health safety

---

## 🛠️ **Management Commands**

### **Schema Management**

```bash
# Show current database status
python3 manage_db.py info

# Create backup
python3 manage_db.py backup

# Create new migration after model changes
python3 manage_db.py new-migration --message "Add new feature"

# Apply pending migrations
python3 manage_db.py migrate

# Rollback if needed
python3 manage_db.py rollback
```

### **Direct Schema Operations**

```bash
# Create schema from scratch
python3 create_schema.py create

# Drop all tables (dangerous!)
python3 create_schema.py drop

# Show detailed schema info
python3 create_schema.py info
```

---

## 🔧 **Database Connection Details**

### **Connection String Format**

```
postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

**Example:**
```
postgresql://emotionai_user:mypassword@emotionai-db.abc123.us-east-1.rds.amazonaws.com:5432/emotionai_prod
```

### **Connection Pool Settings**

```python
# Optimized for t2.micro EC2 instance
DATABASE_POOL_SIZE=5      # Conservative connection pool
DATABASE_MAX_OVERFLOW=10  # Allow some overflow
```

### **SSL Configuration**

```python
# For production, ensure SSL is enabled
DATABASE_URL=postgresql://user:pass@host:5432/db?sslmode=require
```

---

## 🚨 **Troubleshooting**

### **Common Issues:**

#### **1. Connection Refused**
```bash
# Check security groups
aws ec2 describe-security-groups --group-ids sg-xxxxxxxx

# Test network connectivity
telnet your-rds-endpoint.region.rds.amazonaws.com 5432
```

#### **2. Authentication Failed**
```bash
# Verify credentials
psql -h your-rds-endpoint.region.rds.amazonaws.com -U emotionai_user -d emotionai_prod

# Check user permissions in RDS
```

#### **3. Database Does Not Exist**
```sql
-- Connect as master user and create database
CREATE DATABASE emotionai_prod;
CREATE USER emotionai_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE emotionai_prod TO emotionai_user;
```

#### **4. Schema Creation Fails**
```bash
# Check logs for specific error
python3 create_schema.py create

# Verify user has CREATE privileges
# Connect as admin and grant permissions
```

---

## 📊 **Production Considerations**

### **1. Performance**

```sql
-- Monitor connection usage
SELECT count(*) as active_connections, state 
FROM pg_stat_activity 
WHERE datname = 'emotionai_prod' 
GROUP BY state;

-- Check table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::text)) 
FROM pg_tables 
WHERE schemaname = 'public';
```

### **2. Maintenance**

```bash
# Setup automated vacuum (add to crontab)
0 3 * * * PGPASSWORD="$DB_PASSWORD" psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "VACUUM ANALYZE;"

# Monitor slow queries
SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;
```

### **3. Backups**

```bash
# Automated backup script
python3 manage_db.py backup

# RDS automated backups are already configured (7 days retention)
# Manual snapshots for major deployments
```

---

## ✅ **Verification Checklist**

After setup, verify:

- [ ] RDS instance is running
- [ ] Security groups allow EC2 → RDS connection
- [ ] Database `emotionai_prod` exists
- [ ] User `emotionai_user` has correct permissions
- [ ] All 6 tables created successfully
- [ ] Indexes are present
- [ ] API can connect to database (`/health/detailed`)
- [ ] Sample data can be inserted/queried
- [ ] Backup/restore works

---

## 🎉 **Success!**

Your RDS PostgreSQL database is now ready for EmotionAI API production use!

**Next Steps:**
1. Start your API: `sudo systemctl start emotionai`
2. Test functionality: `curl https://yourdomain.com/health/detailed`
3. Monitor performance: `python3 manage_db.py info`
4. Set up monitoring and alerts

Your EmotionAI API now has a robust, scalable PostgreSQL database backend! 🚀