# Local Deployment Guide for AVD Testing

## Quick Setup (Docker - Recommended)

### 1. Set up Environment Variables
Create a `.env` file in the root directory:

```bash
# Database
DATABASE_URL=postgresql://emotionai:password123@localhost:5432/emotionai_db

# LLM Configuration  
OPENAI_API_KEY=your_openai_api_key_here
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Application
SECRET_KEY=your-super-secret-key-change-this-in-production
ENVIRONMENT=development
DEBUG=true

# Redis (for caching)
REDIS_URL=redis://localhost:6379

# CORS - Important for AVD!
CORS_ORIGINS=["*"]
```

### 2. Start Services with Docker
```bash
# Start PostgreSQL and Redis
docker-compose up -d

# This will start:
# - PostgreSQL on port 5432
# - Redis on port 6379
```

### 3. Install Python Dependencies
```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run Database Setup
```bash
# The app will create tables automatically on first run
# Or you can force table creation:
python -c "
import asyncio
from src.infrastructure.config.settings import settings
from src.infrastructure.database.connection import DatabaseConnection

async def setup():
    db = await DatabaseConnection.create(settings)
    await db.create_tables()
    await db.close()

asyncio.run(setup())
"
```

### 5. Start the Backend
```bash
# Method 1: Direct Python
python main.py

# Method 2: With uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Method 3: Production-like
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

## AVD Connection Setup

### Backend URLs for AVD
- **AVD to Host**: `http://10.0.2.2:8000`
- **Local Testing**: `http://localhost:8000`
- **Network Testing**: `http://YOUR_IP:8000`

### Update Flutter App Configuration
In your Flutter app, update the base URL:

```dart
// For AVD
const String baseUrl = 'http://10.0.2.2:8000';

// For physical device on same network
const String baseUrl = 'http://192.168.1.XXX:8000'; // Your computer's IP
```

## Manual Setup (Without Docker)

### 1. Install PostgreSQL
```bash
# Windows: Download from postgresql.org
# Mac: brew install postgresql
# Ubuntu: sudo apt-get install postgresql postgresql-contrib

# Create database
psql -U postgres
CREATE DATABASE emotionai_db;
CREATE USER emotionai WITH PASSWORD 'password123';
GRANT ALL PRIVILEGES ON DATABASE emotionai_db TO emotionai;
\q
```

### 2. Install Redis (Optional)
```bash
# Windows: Download from redis.io or use WSL
# Mac: brew install redis
# Ubuntu: sudo apt-get install redis-server

# Start Redis
redis-server
```

### 3. Configure Environment
Update `.env` with your actual database connection:
```
DATABASE_URL=postgresql://emotionai:password123@localhost:5432/emotionai_db
```

## Testing the Deployment

### 1. Health Check
```bash
# Test backend is running
curl http://localhost:8000/health/

# Expected response:
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "2.0.0",
  "environment": "development"
}
```

### 2. Test from AVD
In your Flutter app or browser in AVD:
```
http://10.0.2.2:8000/health/
```

### 3. Test API Endpoints
```bash
# List available agents
curl http://localhost:8000/api/v1/agents

# Register user (test auth)
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123",
    "first_name": "Test",
    "last_name": "User"
  }'
```

## Troubleshooting

### Common Issues

#### 1. **AVD Can't Connect to Backend**
```bash
# Check if backend is accessible
# In Android emulator browser, go to: http://10.0.2.2:8000/health/

# If not working, try:
# - Make sure backend runs on 0.0.0.0, not just localhost
# - Check Windows Firewall
# - Verify port 8000 is not blocked
```

#### 2. **Database Connection Errors**
```bash
# Check PostgreSQL is running
# Windows: Services -> PostgreSQL
# Mac/Linux: systemctl status postgresql

# Test connection
psql -h localhost -U emotionai -d emotionai_db
```

#### 3. **CORS Errors**
Make sure `.env` has:
```
CORS_ORIGINS=["*"]
```

#### 4. **Missing API Keys**
```bash
# For testing without LLM, you can mock responses
# Or get free API keys:
# - OpenAI: platform.openai.com
# - Anthropic: console.anthropic.com
```

### Network Configuration for Physical Device

If testing on physical device instead of AVD:

#### 1. Find Your Computer's IP
```bash
# Windows
ipconfig

# Mac/Linux  
ifconfig
# Look for something like 192.168.1.XXX
```

#### 2. Update Flutter App
```dart
const String baseUrl = 'http://192.168.1.100:8000'; // Your actual IP
```

#### 3. Allow Network Access
```bash
# Windows: Allow Python through Windows Firewall
# Mac: System Preferences -> Security -> Firewall
# Make sure port 8000 is accessible
```

## Development Workflow

### 1. **Start Backend**
```bash
cd /path/to/emotionai-api
docker-compose up -d  # Start databases
python main.py        # Start API server
```

### 2. **Verify Backend**
```bash
# Check health
curl http://localhost:8000/health/

# Check from AVD
# Browser in emulator: http://10.0.2.2:8000/health/
```

### 3. **Update Flutter**
```dart
// In your Flutter app's API client
const String baseUrl = 'http://10.0.2.2:8000';
```

### 4. **Test Integration**
- Register user via Flutter app
- Test chat functionality
- Verify agent responses

## Performance Tips

### 1. **Development Mode**
```bash
# Run with auto-reload for development
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. **Database Optimization**
```bash
# For better performance, increase connection pool
# In .env:
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
```

### 3. **Monitoring**
```bash
# Check detailed health
curl http://localhost:8000/health/detailed

# Monitor logs
# Backend will show request logs in terminal
```

## Next Steps

1. **Start the backend** with the commands above
2. **Test health endpoint** from AVD browser
3. **Update Flutter app** base URL to `http://10.0.2.2:8000`
4. **Test authentication** flow end-to-end
5. **Test chat functionality** with agents

Your backend will be ready for Flutter app testing! 🚀 