# Technology Stack

**Analysis Date:** 2026-03-19

## Languages

**Primary:**
- Python 3.11 - Backend FastAPI application, all async code

**Secondary:**
- SQL (PostgreSQL) - Database migrations via Alembic
- JSON - Configuration and data serialization

## Runtime

**Environment:**
- Python 3.11 (via Docker: `python:3.11-slim`)

**Package Manager:**
- pip - Direct requirements.txt management
- Lockfile: `requirements.txt` (frozen versions)

**Installation:**
```bash
pip install -r requirements.txt
```

## Frameworks

**Core:**
- FastAPI 0.104.1+ - REST API framework with async support
- Uvicorn 0.24.0+ - ASGI server (with event loop optimization via uvloop)

**Database/ORM:**
- SQLAlchemy 2.0.0+ - Async ORM with asyncpg driver
- asyncpg 0.29.0 - Async PostgreSQL client library
- Alembic 1.12.0+ - Database migration management

**Authentication/Security:**
- PyJWT 2.8.5–2.x - JWT token encoding/decoding (HS256 algorithm)
- passlib 1.7.4+ with bcrypt - Password hashing
- python-jose 3.3.0+ - Cryptography for token operations

**AI/LLM:**
- LangChain 0.0.300+ - Agent framework and prompt management
- OpenAI 1.0.0+ - GPT-4 and GPT-4o-mini client
- Anthropic 0.25.0+ - Claude API client (fallback/alternative provider)

**Caching/Events:**
- Redis 5.0.1+ - Event bus and caching
- redis.asyncio - Async Redis client
- aiocache 0.12.0+ - Async cache abstraction layer

**Vector/Semantic Search:**
- chromadb 0.4.0+ - Vector database for embeddings
- qdrant-client 1.7.0+ - Optional vector database client

**Data Validation:**
- Pydantic 2.0.0+ - Request/response schema validation
- pydantic-settings 2.0.0+ - Environment configuration management
- email-validator 2.0.0+ - Email format validation

**Dependency Injection:**
- dependency-injector 4.41.0+ - Service container for Clean Architecture

**Monitoring/Observability:**
- boto3 1.34.0+ - AWS CloudWatch Logs client (mobile event logging)
- botocore 1.34.0+ - AWS SDK core

**HTTP/Networking:**
- httpx 0.25.0+ - Async HTTP client for outbound calls
- aiofiles 23.2.1+ - Async file I/O

**Development/Performance:**
- uvloop 0.19.0+ - Drop-in faster event loop replacement
- httptools 0.6.0+ - C-accelerated HTTP parsing
- psutil 5.9.0+ - System monitoring for health checks
- greenlet 2.0.0+ - Required for SQLAlchemy async support

**Testing:**
- pytest 7.4.0+ - Test runner
- pytest-asyncio 0.21.0+ - Async test support

**Code Quality (Development):**
- black 23.0.0+ - Code formatter
- isort 5.12.0+ - Import sorting

**Configuration:**
- python-dotenv 1.0.0+ - Load environment variables from `.env`

**Web Framework Extras:**
- python-multipart 0.0.6+ - Form data parsing
- Starlette (via FastAPI) - Async middleware support

## Key Dependencies

**Critical:**
- asyncpg 0.29.0 - Direct async database access; without it, blocking sync calls replace async
- LangChain 0.0.300+ - Powers the AI agent; GPT-4 system prompt management
- OpenAI 1.0.0+ - GPT-4 and GPT-4o-mini for therapy responses and semantic tagging
- FastAPI 0.104.1+ - Async request handling; loss of framework means rewrite routes

**Infrastructure:**
- PostgreSQL 13 (RDS in production, Docker in dev)
- Redis 7 (in-memory event bus and cache)
- boto3 1.34.0+ - AWS CloudWatch Logs for mobile app telemetry

## Configuration

**Environment:**
- Loaded via `src/infrastructure/config/settings.py` using `pydantic-settings`
- Primary file: `.env` (development) or `/etc/emotionai-api.env` (production via systemd)
- Fallback: hardcoded defaults in `Settings` class

**Build:**
- `Dockerfile` (Python 3.11-slim)
- `docker-compose.yml` (dev: postgres:13, redis:7-alpine, api service)
- `setup_database.sql` - Initial schema setup script

**Build command:**
```bash
docker-compose up --build
```

## Platform Requirements

**Development:**
- Docker and Docker Compose
- Python 3.11 (for local non-containerized runs)
- PostgreSQL 13 and Redis 7 (if not using docker-compose)

**Production:**
- AWS EC2 (t3.micro) in eu-west-1
- AWS RDS PostgreSQL 16 (private subnet)
- AWS Redis 7 (managed)
- Nginx (TLS termination, WS proxy)
- systemd service on EC2

**Deployment target:**
- Linux x86_64 (Ubuntu on EC2)
- IMDSv2 enforced on EC2 for security

---

*Stack analysis: 2026-03-19*
