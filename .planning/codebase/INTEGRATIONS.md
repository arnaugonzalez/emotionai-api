# External Integrations

**Analysis Date:** 2026-03-19

## APIs & External Services

**AI & Language Models:**
- OpenAI GPT-4 / GPT-4o-mini - Primary AI therapist agent and semantic tagging
  - SDK/Client: `openai>=1.10,<2`
  - Auth: `OPENAI_API_KEY` (env var)
  - Usage: `src/infrastructure/services/openai_llm_service.py`, `src/infrastructure/services/openai_tagging_service.py`
  - Integration: LangChain agent framework

- Anthropic Claude - Alternative LLM provider (optional)
  - SDK/Client: `anthropic>=0.60,<1`
  - Auth: `ANTHROPIC_API_KEY` (env var, optional)
  - Usage: `src/infrastructure/services/anthropic_llm_service.py`
  - Integration: Fallback provider via `src/infrastructure/external/llm_providers.py`

**Real-Time Communication:**
- WebSocket (FastAPI native) - Calendar updates and real-time notifications
  - Implementation: `src/presentation/api/routers/ws.py`
  - Manager: `src/presentation/api/events/manager.py`
  - Auth: JWT token in query params (`?token=...`)

## Data Storage

**Primary Database:**
- PostgreSQL 16 (RDS on AWS eu-west-1)
  - Connection: `DATABASE_URL` env var (format: `postgresql+asyncpg://user:pass@host:5432/db`)
  - Client: SQLAlchemy 2.0.30+ with asyncpg adapter
  - Pool: 20 base connections, 30 overflow (configurable)
  - SSL: Root cert via `DB_SSL_ROOT_CERT` env var
  - Models: `src/infrastructure/database/models.py`
  - Migrations: Alembic in `migrations/versions/`

**In-Memory Cache & Event Bus:**
- Redis 7 (ElastiCache on AWS or Docker local)
  - Connection: `REDIS_URL` env var (format: `redis://host:port/db`)
  - Client: `redis>=5.1,<6` with `hiredis>=2.2,<4` for protocol performance
  - Usage:
    - Event bus via `src/infrastructure/services/redis_event_bus.py`
    - Cache layer via `aiocache>=0.12`
  - Hostname: `redis` (Docker), `localhost` or AWS ElastiCache endpoint (production)
  - Port: 6379 (default)

**Vector Database (Optional):**
- ChromaDB 0.4.0+ - Semantic embeddings and similarity search (optional)
  - Usage: Semantic record search
  - Client: `chromadb>=0.4.0` (in requirements.txt, not production)

- Qdrant 1.7.0+ - Vector database client (optional)
  - Client: `qdrant-client>=1.7.0` (in requirements.txt, not production)

**File Storage:**
- Local filesystem only - No S3 integration active
- AWS S3 capability present (boto3 available) but not currently used

## Authentication & Identity

**Auth Provider:**
- Custom JWT-based implementation
  - Implementation: `src/presentation/api/routers/auth_router.py`
  - Token format: HS256 (HMAC with SHA-256)
  - Secret: `SECRET_KEY` env var (32+ character random string)
  - Algorithm: `HS256` (fixed)
  - Access token expiry: Configurable via `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 minutes)
  - Refresh token expiry: Configurable via `REFRESH_TOKEN_EXPIRE_DAYS` (default 30 days)
  - Library: PyJWT 2.8+ and python-jose 3.3.0

**Password Security:**
- Hashing: bcrypt via Passlib 1.7.4
  - Cost factor: Default (12 rounds, configurable)
  - Implementation: `src/domain/entities/user.py`

**Current Known Issues:**
- No token refresh mechanism — clients face silent 401s after access token expiry (XC-002)
- Auth bypass via hardcoded UUID fallback in `src/presentation/api/routers/deps.py` (P0 security issue)

## Monitoring & Observability

**Logging:**
- Framework: structlog 25.0+ (structured JSON logging in production)
- Fallback: Python stdlib logging (development)
- Implementation: `src/infrastructure/config/settings.py` (configurable log level)
- Level: Controlled via `LOG_LEVEL` env var (default INFO)

**Error Tracking:**
- Sentry (optional) - sentry-sdk 2.6+ with FastAPI integration
  - Configuration: `SENTRY_DSN` (not in .env.example — requires explicit setup)
  - Not currently initialized but SDK is available

**Cloud Logging:**
- AWS CloudWatch Logs - Mobile app error logs
  - Region: `mobile_logs_region` (default eu-west-1)
  - Log Group: `mobile_logs_group` (default `/emotionai/mobile-app`)
  - Implementation: `src/infrastructure/observability/cloudwatch_logger.py`
  - Max throughput: 500 logs per minute (configurable via `MOBILE_LOGS_MAX_PER_MIN`)
  - Auth: IAM role on EC2 (`emotionai-ec2-ssm`)

**Health Checks:**
- Endpoint: `/health` (no auth required)
- Usage: Mobile app connectivity check
- Utilities: `psutil>=5.9` for system monitoring

## CI/CD & Deployment

**Hosting:**
- AWS EC2 (t3.micro) in eu-west-1
- Reverse proxy: Nginx with TLS termination
- Process management: systemd service
- Service supervisor: EC2 running under systemd

**CI Pipeline:**
- GitHub Actions (via `.github/workflows/`)
- S3 artifact push: `.github/workflows/aws_s3_push.yml`
- No automated tests in CI (integration tests exist locally only)

**Deployment Process:**
- Infrastructure as Code: Terraform (HCL) in `aws_infra_terraformer/`
- Secrets: AWS Systems Manager Parameter Store (`/emotionai/prod/*`)
- IMDSv2 enforced on all EC2 instances
- Deployment scripts: Bash and PowerShell in `scripts_emotionai/` and `deploy/`

## Environment Configuration

**Required env vars for startup:**
- `OPENAI_API_KEY` - OpenAI API key (sk-...)
- `SECRET_KEY` - JWT signing secret (32+ chars)
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string (development: defaults to localhost:6379)

**Optional env vars (with defaults):**
- `ENVIRONMENT` - development/production (default: development)
- `DEBUG` - Enable debug mode (default: False)
- `OPENAI_MODEL` - LLM model (default: gpt-4)
- `OPENAI_MAX_TOKENS` - Response token limit (default: 500)
- `OPENAI_TEMPERATURE` - LLM creativity (default: 0.7)
- `ANTHROPIC_API_KEY` - Claude API key (optional)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - JWT expiry (default: 30)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiry (default: 30)
- `LOG_LEVEL` - Logging verbosity (default: INFO)
- `CORS_ORIGINS` - CORS allowed origins (default: * for dev)
- `RATE_LIMIT_REQUESTS` - Requests per hour (default: 100)
- `AWS_REGION` - AWS region (default: us-west-1, should be eu-west-1 for prod)
- `MOBILE_LOGS_ENABLED` - CloudWatch logging (default: False)
- `EC2_PUBLIC_IP` - EC2 instance IP for client config

**Secrets location:**
- Development: `.env` file (gitignored)
- Production: AWS Systems Manager Parameter Store (`/emotionai/prod/`)
- Template: `.env.example` (no secrets, just structure)

## Webhooks & Callbacks

**Incoming Webhooks:**
- None currently implemented

**Outgoing Webhooks:**
- WebSocket broadcasts from server to connected clients via `/ws/calendar`
- Event types: Calendar events, real-time notifications
- Implementation: `src/presentation/api/routers/ws.py` + `src/presentation/api/events/manager.py`

## Local Development Services (Docker Compose)

**Database Service:**
- Image: `postgres:13`
- Port: 5432
- Credentials: emotionai/password123 (development only)
- Health check: pg_isready every 5s, 10 retries
- Network: emotionai-network

**Cache Service:**
- Image: `redis:7-alpine`
- Port: 6379
- Health check: redis-cli ping every 5s, 5 retries
- Network: emotionai-network

**API Service:**
- Build: Dockerfile (Python 3.11-slim)
- Port: 8000
- Reload: Enabled (uvicorn --reload)
- Dependencies: Waits for db and redis healthchecks
- Volume: Current directory mounted for code reload
- Network: emotionai-network

## Integration Patterns

**LLM Integration (Therapy Agent):**
1. Request comes to `POST /v1/api/chat`
2. Handler in `src/presentation/api/routers/chat.py`
3. Use case: `src/application/chat/use_cases/agent_chat_use_case.py`
4. Service: `LangChainAgentService` (implements `IAgentService`)
5. LLM Factory: `src/infrastructure/external/llm_providers.py` (selects OpenAI or Anthropic)
6. Memory: Stored in Redis via LangChain integration
7. Response: `TherapyResponse` DTO with `crisis_detected: bool` flag

**Semantic Tagging Pipeline (Secondary):**
1. After chat response generated
2. Service: `OpenAITaggingService` in `src/infrastructure/services/openai_tagging_service.py`
3. Uses GPT-4o-mini for cost efficiency
4. Tags stored in `EmotionalRecordModel` via `src/domain/records/`
5. Fire-and-forget via Redis event bus (no blocking)

**Real-Time Calendar Updates:**
1. WebSocket client connects to `/ws/calendar?token=<JWT>`
2. Authenticated via JWT decode in `src/presentation/api/routers/ws.py`
3. Manager: `CalendarEventManager` maintains connected clients
4. Event broadcast: `broadcast_calendar_event(type, payload)` -> all connected clients
5. Protocol: JSON messages with `{type, payload}`

**Token Usage Tracking:**
1. After every chat message
2. Repository: `SqlAlchemyTokenUsageRepository` in `src/infrastructure/usage/repositories/`
3. Mobile polls `/v1/api/usage` to check remaining budget
4. Cost: Tracked via `TOKEN_COST_PER_1K` setting (default: 0.002)

---

*Integration audit: 2026-03-19*
