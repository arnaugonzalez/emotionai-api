# EmotionAI API

AI-powered mental health and wellness API with personalized therapeutic and wellness agents.

## Features

- **Personalized AI Agents**: Specialized therapy and wellness agents with different personalities
- **Emotional Tracking**: Record and analyze emotional states over time
- **Breathing Sessions**: Track guided breathing exercises and patterns
- **Conversation Memory**: Agents maintain context and memory across sessions
- **Multiple LLM Support**: OpenAI and Anthropic language models
- **RESTful API**: Complete FastAPI-based backend with authentication
- **Docker Support**: Easy deployment with Docker Compose

## Architecture

### Agent System
- **BasePersonalizedAgent**: Foundation class for all agents
- **TherapyAgent**: Specialized for therapeutic conversations and mental health support
- **WellnessAgent**: Focused on general wellness, mindfulness, and self-care

### Core Components
- **LLMFactory**: Manages language model instances with caching
- **AgentManager**: Handles agent lifecycle and user sessions
- **Database Models**: SQLAlchemy models for users, emotions, breathing sessions, etc.

## Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL
- Docker & Docker Compose (recommended)

### Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd emotionai-api
```

2. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Using Docker (Recommended):**
```bash
docker-compose up -d --build
```

4. **Or run locally:**
```bash
# Install dependencies
pip install -r requirements.txt

# Set up database
# Make sure PostgreSQL is running and database exists

# Run the application
uvicorn app.main:app --reload
```

### Configuration

Key environment variables to set in `.env`:

```env
# Required
DATABASE_URL=postgresql://user:password@localhost/emotionai
SECRET_KEY=your-super-secret-key
OPENAI_API_KEY=your-openai-api-key

# Optional
ANTHROPIC_API_KEY=your-anthropic-api-key
REDIS_URL=redis://localhost:6379
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh token

### AI Agents
- `POST /agents/chat` - Chat with personalized agent
- `GET /agents/status` - Get agent status
- `POST /agents/clear-memory` - Clear agent memory
- `POST /agents/emotional-record` - Add emotional data
- `POST /agents/breathing-session` - Add breathing session
- `PUT /agents/context` - Update agent context

### Data Management
- `GET/POST /emotional_records/` - Emotional records
- `GET/POST /breathing_sessions/` - Breathing sessions
- `GET/POST /breathing_patterns/` - Breathing patterns
- `GET/POST /custom_emotions/` - Custom emotions

### Monitoring
- `GET /health` - Health check
- `GET /agents/admin/stats` - Agent statistics

## Agent Types

### Therapy Agent
Specialized for therapeutic conversations with:
- Crisis detection and response
- Session tracking and progress notes
- Coping strategy suggestions
- Goal setting and monitoring

### Wellness Agent
Focused on general wellness with:
- Mindfulness and meditation guidance
- Stress management techniques
- Lifestyle recommendations
- Mood trend analysis

## Personality Types

Agents can be configured with different personalities:
- **empathetic_supportive**: Warm, validating responses
- **encouraging_motivational**: Positive, strength-focused
- **analytical_practical**: Structured, solution-oriented
- **mindful_contemplative**: Present-moment awareness
- **creative_expressive**: Artistic and creative approaches

## Database Schema

### Core Tables
- `users`: User accounts with agent preferences
- `emotional_records`: Emotional state tracking
- `breathing_sessions`: Breathing exercise data
- `breathing_patterns`: Available breathing techniques
- `ai_conversation_memories`: Agent conversation summaries

## Development

### Project Structure
```
emotionai-api/
├── agents/                 # Agent implementations
├── api/                   # API route handlers
├── app/                   # FastAPI application
│   ├── routers/          # API routers
│   ├── models.py         # Database models
│   ├── schemas.py        # Pydantic schemas
│   └── main.py           # Application entry point
├── core/                 # Core utilities
├── services/             # Business logic services
├── models/              # Response models
└── requirements.txt
```

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
isort .
```

## Deployment

### Docker Compose
The included `docker-compose.yml` sets up:
- PostgreSQL database
- Redis (optional)
- API application

### Environment Variables
See `.env.example` for all available configuration options.

### Health Monitoring
- Health check endpoint: `GET /health`
- Application logs include agent activity
- Database connection monitoring

## Security

- JWT-based authentication
- Password hashing with bcrypt
- Environment-based configuration
- Input validation with Pydantic
- Rate limiting support

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license information here]

## Support

For support and questions:
- Create an issue in the repository
- Check the documentation in `/docs`
- Review the API documentation at `/docs` when running

---

**Note**: This is a mental health application. Always encourage users to seek professional help when appropriate and include crisis resources in your deployment.