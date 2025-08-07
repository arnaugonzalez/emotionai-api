# EmotionAI API Setup Guide

## Overview
This guide will help you set up the EmotionAI API after the successful migration from monolithic to agent-based architecture.

## Prerequisites

### System Requirements
- **Python 3.8+** (recommended: 3.9 or 3.10)
- **PostgreSQL 12+**
- **Git**
- **Docker & Docker Compose** (recommended for easy setup)

### API Keys Required
- **OpenAI API Key** (required)
- **Anthropic API Key** (optional, for Claude support)

## Quick Setup (Docker - Recommended)

### 1. Clone and Enter Directory
```bash
git clone <your-repo-url>
cd emotionai-api
```

### 2. Environment Configuration
Copy the environment template:
```bash
# Create your environment file
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# Required - Replace with your actual values
DATABASE_URL=postgresql://user:password@db/emotionai
SECRET_KEY=your-super-secret-key-change-this-in-production
OPENAI_API_KEY=sk-your-openai-api-key

# Optional
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

### 3. Start with Docker
```bash
# Start all services (database + API)
docker-compose up -d --build

# Check if everything is running
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Verify Setup
Test the API:
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

## Manual Setup (Without Docker)

### 1. Install Python Dependencies
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup
Install and start PostgreSQL, then create database:
```sql
CREATE DATABASE emotionai;
CREATE USER emotionai_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE emotionai TO emotionai_user;
```

### 3. Environment Configuration
```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://emotionai_user:your_password@localhost/emotionai
SECRET_KEY=your-super-secret-key
OPENAI_API_KEY=sk-your-openai-api-key
```

### 4. Run the Application
```bash
# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Testing the Installation

### 1. Run Integration Tests
```bash
python test_integration.py
```

### 2. Test API Endpoints

#### Register a User
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

#### Login
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpassword123"
  }'
```

#### Test Agent Chat (requires auth token)
```bash
curl -X POST http://localhost:8000/agents/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "message": "Hello, I am feeling stressed today",
    "agent_type": "therapy"
  }'
```

## Configuration Options

### Required Environment Variables
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT signing key (use a secure random string)
- `OPENAI_API_KEY`: Your OpenAI API key

### Optional Environment Variables
- `ANTHROPIC_API_KEY`: For Claude model support
- `REDIS_URL`: For caching (default: redis://localhost:6379)
- `MAX_MEMORY_ITEMS`: Agent memory limit (default: 100)
- `AGENT_TIMEOUT`: Agent response timeout in seconds (default: 30)
- `DEBUG`: Enable debug mode (default: false)

### Agent Configuration
Users can be assigned different agent personalities:
- `empathetic_supportive`: Warm, validating responses
- `encouraging_motivational`: Positive, strength-focused
- `analytical_practical`: Structured, solution-oriented
- `mindful_contemplative`: Present-moment awareness
- `creative_expressive`: Artistic and creative approaches

## Database Schema

The API will automatically create tables on startup. Key tables include:

### Users Table
- Basic user authentication
- Agent personality preferences
- Profile data (JSON)
- Agent preferences (JSON)

### Emotional Records Table
- Emotion tracking with intensity (1-10)
- Context and location information
- Custom emotion support

### Breathing Sessions Table
- Breathing exercise tracking
- Pattern names and durations
- Session metadata (JSON)

## API Features Available

### 🤖 AI Agents
- **Therapy Agent**: Mental health support with crisis detection
- **Wellness Agent**: Mindfulness and wellness guidance
- **Personality Types**: 5 different agent personalities
- **Memory**: Persistent conversation context
- **Safety**: Crisis detection and appropriate responses

### 📊 Data Tracking
- **Emotional Records**: Track emotions with context
- **Breathing Sessions**: Monitor breathing exercises
- **Custom Emotions**: User-defined emotional states
- **Progress Monitoring**: Long-term trend analysis

### 🔐 Security
- **JWT Authentication**: Secure token-based auth
- **Password Hashing**: bcrypt password protection
- **Input Validation**: Comprehensive request validation
- **Rate Limiting**: Configurable request limits

## Troubleshooting

### Common Issues

#### 1. "No module named 'langchain'"
```bash
pip install -r requirements.txt
```

#### 2. "Connection refused" (Database)
- Ensure PostgreSQL is running
- Check DATABASE_URL in .env
- Verify database exists and user has permissions

#### 3. "Agent manager not initialized"
- Check that the FastAPI app is starting correctly
- Verify all dependencies are installed
- Check logs for initialization errors

#### 4. OpenAI API errors
- Verify OPENAI_API_KEY is correct
- Check API key has sufficient credits
- Ensure API key has necessary permissions

### Getting Help

1. **Check Logs**: 
   ```bash
   docker-compose logs -f  # Docker setup
   # or check console output for manual setup
   ```

2. **API Documentation**: Visit `http://localhost:8000/docs`

3. **Health Check**: `curl http://localhost:8000/health`

4. **Test Components**: `python test_integration.py`

## Next Steps

After successful setup:

1. **Frontend Integration**: Update your Flutter app to use the new API endpoints
2. **API Documentation**: Explore available endpoints at `/docs`
3. **Customization**: Modify agent personalities and system prompts
4. **Monitoring**: Set up logging and monitoring for production
5. **Scaling**: Configure Redis for session management in production

---

🎉 **Congratulations!** Your EmotionAI API is now ready with the complete agent-based architecture. 