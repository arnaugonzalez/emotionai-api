# External Integrations

**Analysis Date:** 2026-03-19

## APIs & External Services

**OpenAI:**
- Service: GPT-4 (therapy responses) and GPT-4o-mini (semantic tagging)
- SDK/Client: `openai 1.0.0+` → `openai.AsyncOpenAI`
- Auth: `OPENAI_API_KEY` env var
- Files: `src/infrastructure/services/langchain_agent_service.py`, `src/infrastructure/services/openai_tagging_service.py`
- Usage:
  - **Therapy**: LangChain agent uses GPT-4 with system prompts for therapeutic responses (crisis detection included)
  - **Tagging**: GPT-4o-mini extracts semantic tags from chat messages and emotional records

**Anthropic Claude:**
- Service: Claude API (alternative/fallback LLM provider)
- SDK/Client: `anthropic 0.25.0+` (optional)
- Auth: `ANTHROPIC_API_KEY` env var (optional; requires at least OpenAI or Anthropic)
- Files: `src/infrastructure/config/settings.py` (lines 49–51)
- Usage: Fallback LLM provider if OpenAI unavailable; configured in `Settings.get_llm_config()`

## Data Storage

**Databases:**
- **PostgreSQL 13/16** (RDS in production, Docker in dev)
  - Connection: `DATABASE_URL` env var → `postgresql+asyncpg://user:pass@host:5432/emotionai_db`
  - Client: SQLAlchemy 2.0+ with asyncpg driver
  - Connection pool: 20 base + 30 overflow (`settings.py` lines 34–35)
  - Tables: Users, conversations, emotional records, breathing sessions, profiles, agent personalities
  - Migrations: Alembic in `migrations/versions/` (single file: `001_initial_schema.py`)
  - SSL: Optional RDS cert at `settings.db_ssl_root_cert` (default: `/etc/ssl/certs/aws-rds.pem`)

**In-Memory/Cache:**
- **Redis 7** (on Docker as `redis:7-alpine`)
  - Connection: `REDIS_URL` env var → `redis://localhost:6379` or `redis://redis:6379` (docker)
  - Database: `REDIS_DB` env var (default: 0)
  - Password: `REDIS_PASSWORD` env var (optional)
  - Usage:
    - **Event bus**: `RedisEventBus` publishes domain events to Redis pub/sub
    - **Caching**: aiocache integration
    - **Session state**: Conversation memory and user context

**File Storage:**
- Local filesystem only (no S3 integration currently active)

**Vector Database:**
- **Chromadb 0.4.0+** - In-memory or persistent vector storage for embeddings
- **Qdrant 1.7.0+** (optional) - Alternative vector database

## Authentication & Identity

**Auth Provider:**
- Custom JWT implementation (no external OAuth provider)

**Implementation:**
- **Token generation**: `src/presentation/api/routers/auth.py` lines 29–38
  - Algorithm: HS256 (symmetric)
  - Secret: `SECRET_KEY` env var
  - Payload: `{ "sub": user_id, "typ": "access|refresh", "iat": timestamp, "exp": expiry, "iss": "emotionai-api" }`
- **Access token**: Expires in `ACCESS_TOKEN_EXPIRE_MINUTES` env var (default: 30 min)
- **Refresh token**: Expires in `REFRESH_TOKEN_EXPIRE_DAYS` env var (default: 30 days)
- **Password hashing**: bcrypt via passlib (see `auth.py` line 26)
- **Verification**: `src/presentation/dependencies.py` → `get_current_user_id()` decodes and validates JWT

**Auth files:**
- `src/presentation/api/routers/auth.py` - Register, login, token creation
- `src/presentation/api/routers/deps.py` - HTTP endpoint dependency injection
- `src/presentation/dependencies.py` - Centralized JWT validation
- `src/presentation/api/routers/ws.py` - WebSocket JWT auth (query param)

**Known issue:** Hardcoded UUID fallback in `deps.py` allows auth bypass (P0 security debt).

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry/Rollbar integration)
- Logging via Python `logging` module to stdout

**Logs:**
- **Backend logs**: Python logging to console/stderr (log level configurable via `LOG_LEVEL` env var)
- **Mobile app logs**: AWS CloudWatch Logs integration
  - Client: `boto3.client('logs')` in `src/infrastructure/observability/cloudwatch_logger.py`
  - Log group: `MOBILE_LOGS_GROUP` env var (default: `/emotionai/mobile-app`)
  - Region: `MOBILE_LOGS_REGION` env var (default: `eu-west-1`)
  - Rate limit: `MOBILE_LOGS_MAX_PER_MIN` env var (default: 500 events/min)

**Metrics:**
- Health check endpoint: `GET /health` (no auth required)
- Uvicorn metrics: Optional prometheus-style metrics
- System metrics: `psutil 5.9.0+` for health checks

**Health check interval:** `HEALTH_CHECK_INTERVAL` env var (default: 60 sec)

## CI/CD & Deployment

**Hosting:**
- AWS EC2 t3.micro in eu-west-1 (public subnet)
- Nginx reverse proxy (TLS termination, HSTS, WebSocket proxy)
- systemd service: `emotionai-api.service`

**CI Pipeline:**
- None detected in main repo
- Manual or script-based deployment via `scripts_emotionai/` bash/PowerShell scripts

**Deployment artifacts:**
- Docker image built locally or via docker-compose
- Pushed to Docker Hub or AWS ECR (not detected in current config)

## Environment Configuration

**Required env vars:**

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | - | JWT signing key (must be set, no default) |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection |
| `OPENAI_API_KEY` | - | OpenAI API key (or `ANTHROPIC_API_KEY`) |
| `ENVIRONMENT` | `development` | `development`, `testing`, `production` |
| `OPENAI_MODEL` | `gpt-4` | Model name for therapy responses |
| `ANTHROPIC_MODEL` | `claude-3-5-sonnet-latest` | Claude model (fallback) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | JWT access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 30 | Refresh token TTL |
| `CORS_ORIGINS` | `["*"]` | Comma-separated list of allowed origins |
| `AWS_REGION` | `us-west-1` | AWS region for services |
| `LOG_LEVEL` | `INFO` | Python logging level |
| `MOBILE_LOGS_ENABLED` | `false` | Enable CloudWatch mobile logs |
| `MOBILE_LOGS_REGION` | `eu-west-1` | CloudWatch region for mobile logs |
| `MOBILE_LOGS_GROUP` | `/emotionai/mobile-app` | CloudWatch log group name |

**Secrets location:**
- Development: `.env` file (git-ignored)
- Production: `/etc/emotionai-api.env` (managed by systemd/SSM, never in repo)
- AWS SSM Parameter Store: `/emotionai/prod/*` paths (per CLAUDE.md)

**Note:** No `.env` file is ever committed. See `src/infrastructure/config/settings.py` lines 23–25.

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

**Real-time Communication:**
- WebSocket endpoint: `GET /ws/calendar` (JWT auth via query param)
- Manager: `CalendarEventManager` in `src/presentation/api/events/manager.py`
- Protocol: JSON messages over ws:// or wss://

## Third-Party Integrations Summary

**Direct API calls:**
1. OpenAI (GPT-4, GPT-4o-mini) - async via `openai.AsyncOpenAI`
2. Anthropic Claude - async via `anthropic` SDK (optional fallback)
3. AWS CloudWatch Logs - sync via `boto3.client('logs')`

**Protocol/Message Formats:**
- REST (FastAPI) - JSON request/response
- WebSocket - JSON messages for real-time events
- Redis pub/sub - JSON-serialized domain events
- PostgreSQL - SQL via SQLAlchemy ORM

---

*Integration audit: 2026-03-19*
