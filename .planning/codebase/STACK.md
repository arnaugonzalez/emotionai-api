# Technology Stack

**Analysis Date:** 2026-03-19

## Languages

**Primary:**
- Python 3.11+ (Docker: 3.11-slim, Local: 3.12.3) - All backend code, APIs, services, database migrations

**Secondary:**
- SQL (PostgreSQL dialect) - Database schema and migrations via Alembic
- JavaScript/TypeScript - Not used in API (Flutter app only)

## Runtime

**Environment:**
- Python 3.11 (specified in `Dockerfile`)
- Running on Python 3.12.3 in development

**Package Manager:**
- pip (Python Package Installer)
- Lockfile: No `poetry.lock` or `pipenv.lock` — uses `requirements.txt` and `requirements-production.txt`

## Frameworks

**Core:**
- FastAPI 0.104.1+ - REST API framework, HTTP routing, validation
- Uvicorn 0.24.0+ - ASGI server for FastAPI
- Gunicorn 22.0+ - Production WSGI/ASGI application server (production deployment)

**ORM & Database:**
- SQLAlchemy 2.0.30+ - ORM for database operations, async support
- Alembic 1.13+ - Database migrations and schema versioning
- asyncpg 0.29+ - Async PostgreSQL adapter
- psycopg2-binary 2.9.9+ - PostgreSQL adapter (fallback/compatibility)

**Testing:**
- pytest 7.4.0+ - Test runner and framework
- pytest-asyncio 0.21.0+ - Async test support for FastAPI/SQLAlchemy

**AI/LLM Integration:**
- LangChain 0.3.16+ - Agent framework, memory management, prompt orchestration
- OpenAI 1.10+ - GPT-4 / GPT-4o-mini API client
- Anthropic 0.60+ - Claude API client (optional provider)
- langchain-openai 0.3+ - LangChain-OpenAI integration bridge

**Authentication & Security:**
- PyJWT 2.8+ - JWT token encoding/decoding (HS256)
- Passlib 1.7.4 - Password hashing with bcrypt
- python-jose 3.3.0 - Alternative JWT handling (cryptography-backed)
- python-multipart 0.0.20+ - Multipart form data handling

**Configuration & Validation:**
- Pydantic 2.9+ - Data validation, settings management, JSON serialization
- pydantic-settings 2.6+ - Environment variable configuration binding
- python-dotenv 1.0+ - `.env` file loading

**HTTP & Networking:**
- httpx 0.27+ - Async HTTP client for external API calls
- aiohttp 3.9+ - Async HTTP client/server library
- aiofiles 23.2.1+ - Async file I/O

**Caching & Event Bus:**
- Redis 5.1+ - In-memory cache, event bus, session storage
- redis 5.1+ - Python Redis client
- hiredis 2.2+ - C parser for Redis protocol (performance)
- aiocache 0.12.0+ - Async caching decorator library

**Development Tools:**
- black 23.0.0+ - Code formatter
- isort 5.12.0+ - Import sorting
- email-validator 2.0.0+ - Email validation

**Performance & Observability:**
- uvloop 0.19.0+ - High-performance event loop for uvicorn
- httptools 0.6.0+ - Fast HTTP parsing for uvicorn
- psutil 5.9.0+ - System monitoring, health checks
- structlog 25.0+ - Structured logging (JSON output)
- sentry-sdk 2.6+ - Error tracking and performance monitoring (production)

**AWS Integration:**
- boto3 1.34+ - AWS SDK for CloudWatch Logs, S3, SSM Parameter Store
- botocore 1.34+ - Low-level AWS API

**Database Support (Optional/Legacy):**
- greenlet 3.0+ - Lightweight threading for SQLAlchemy async
- chromadb 0.4.0+ - Vector database (embeddings, semantic search)
- qdrant-client 1.7.0+ - Vector database client (Qdrant)

**Utilities:**
- typing-extensions 4.13+ - Type hints compatibility
- python-dateutil 2.9+ - Date/time utilities
- orjson 3.10+ - Fast JSON serialization (faster than stdlib json)

## Configuration

**Environment:**
- Loaded via Pydantic `BaseSettings` from `src/infrastructure/config/settings.py`
- Configuration from `.env` file (development) or `/etc/emotionai-api.env` (production)
- Environment variables override file settings

**Key Config Sources:**
- `.env.example` - Template with required and optional settings
- `src/infrastructure/config/settings.py` - Settings class with validation and defaults
- Docker environment variables override via `docker-compose.yml`

**Build & Container:**
- Dockerfile: Python 3.11-slim base image
- System dependencies: gcc, libpq-dev (for asyncpg compilation)
- Docker Compose: Orchestrates postgres, redis, and API containers

## Platform Requirements

**Development:**
- Python 3.11+ installed locally
- Docker and Docker Compose for local services
- PostgreSQL 13+ (via Docker or local)
- Redis 7+ (via Docker or local)
- OpenAI API key (`OPENAI_API_KEY`)
- JWT secret key (`SECRET_KEY`)

**Production:**
- Python 3.11+ runtime
- PostgreSQL 16 (RDS on AWS eu-west-1)
- Redis 7 (ElastiCache on AWS)
- AWS EC2 instance (t3.micro)
- Nginx reverse proxy with TLS termination
- systemd service management
- SSM Parameter Store for secrets (AWS Systems Manager)
- IAM role: `emotionai-ec2-ssm`
- IMDSv2 enforced on EC2

**Test Environment:**
- pytest configuration (via command line or defaults)
- Docker services running for integration tests
- No pytest.ini, setup.cfg, or pyproject.toml test configuration found — uses pytest defaults

## Dependency Pinning Strategy

**Development (`requirements.txt`):**
- Loose pinning: `>=X.Y.Z` (allows minor/patch updates)
- Includes optional/development tools: pytest, black, isort
- Designed for flexibility during development

**Production (`requirements-production.txt`):**
- Strict semantic versioning: `>=X.Y,<X.Z` (major.minor bounds)
- No test dependencies (pytest, black, isort excluded)
- No optional packages (chromadb, qdrant-client excluded)
- Optimized for stability: SQLAlchemy 2.0.30+, asyncpg 0.29+, OpenAI 1.10+
- Includes production logging: structlog 25.0+, sentry-sdk 2.6+

---

*Stack analysis: 2026-03-19*
