# Codebase Structure

**Analysis Date:** 2026-03-19

## Directory Layout

```
emotionai-api/
├── main.py                           # FastAPI app factory, lifespan, exception handlers
├── docker-compose.yml                # Local dev: postgres:16, redis:7, uvicorn
├── Dockerfile                        # Production container image
├── pyproject.toml                    # Python dependencies, Poetry config
├── alembic/                          # Database migrations
│   └── versions/
│       └── 001_initial_schema.py     # Single migration file - all schema
├── tests/                            # Integration tests
│   └── test_*.py                     # Test files (no unit tests yet)
├── migrations/                       # Alembic env (alembic.ini, env.py)
├── scripts_emotionai/                # Dev and deploy scripts (shared repo-level)
├── src/
│   ├── __init__.py                   # Package marker, version import
│   ├── _version.py                   # Version string
│   ├── domain/                       # Layer 1: Pure business logic
│   │   ├── entities/
│   │   │   └── user.py               # User entity with business methods
│   │   ├── value_objects/
│   │   │   ├── user_profile.py       # User profile value object (immutable)
│   │   │   └── agent_personality.py  # Agent personality enum
│   │   ├── events/
│   │   │   ├── interfaces.py         # IEventRepository contract
│   │   │   └── domain_events.py      # UserCreatedEvent, UserProfileUpdatedEvent
│   │   ├── users/
│   │   │   └── interfaces.py         # IUserRepository abstract methods
│   │   ├── records/
│   │   │   └── interfaces.py         # IEmotionalRecordRepository contract
│   │   ├── breathing/
│   │   │   └── interfaces.py         # IBreathingSessionRepository contract
│   │   ├── chat/
│   │   │   ├── interfaces.py         # IAgentConversationRepository contract
│   │   │   └── entities.py           # Conversation, ConversationMessage entities
│   │   ├── analytics/
│   │   │   └── interfaces.py         # IAnalyticsRepository contract
│   │   └── usage/
│   │       └── interfaces.py         # ITokenUsageRepository contract
│   │
│   ├── application/                  # Layer 2: Use cases, service contracts, DTOs
│   │   ├── chat/
│   │   │   └── use_cases/
│   │   │       └── agent_chat_use_case.py  # Main chat orchestration (complex)
│   │   ├── usage/
│   │   │   └── use_cases/
│   │   │       └── get_monthly_usage_use_case.py  # Token usage query (simple)
│   │   ├── services/
│   │   │   ├── agent_service.py      # IAgentService interface
│   │   │   ├── llm_service.py        # ILLMService interface
│   │   │   ├── event_bus.py          # IEventBus interface (Redis)
│   │   │   ├── tagging_service.py    # ITaggingService interface
│   │   │   ├── user_knowledge_service.py  # IUserKnowledgeService interface
│   │   │   ├── similarity_search_service.py  # ISimilaritySearchService interface
│   │   │   └── profile_service.py    # IProfileService interface
│   │   ├── tagging/
│   │   │   └── services/
│   │   │       └── tagging_service.py  # Tagging service interface location
│   │   ├── dtos/
│   │   │   ├── chat_dtos.py          # ChatResponse, ConversationHistoryResponse
│   │   │   └── profile_dtos.py       # ProfileDTO, related types
│   │   └── exceptions.py             # ApplicationException base class
│   │
│   ├── infrastructure/               # Layer 3: Implementation, persistence, external services
│   │   ├── container.py              # ApplicationContainer (DI composition root) ← KEY FILE
│   │   ├── config/
│   │   │   └── settings.py           # Pydantic Settings (env config)
│   │   ├── database/
│   │   │   ├── connection.py         # DatabaseConnection (async pool, session factory)
│   │   │   └── models.py             # SQLAlchemy ORM models (UserModel, ConversationModel, etc.)
│   │   ├── repositories/
│   │   │   └── sqlalchemy_user_repository.py  # IUserRepository implementation
│   │   ├── records/
│   │   │   └── repositories/
│   │   │       └── sqlalchemy_emotional_repository.py  # IEmotionalRecordRepository impl
│   │   ├── breathing/
│   │   │   └── repositories/
│   │   │       └── sqlalchemy_breathing_repository.py  # IBreathingSessionRepository impl
│   │   ├── conversations/
│   │   │   └── repositories/
│   │   │       └── sqlalchemy_conversation_repository.py  # IAgentConversationRepository impl
│   │   ├── events/
│   │   │   └── repositories/
│   │   │       └── sqlalchemy_event_repository.py  # IEventRepository impl
│   │   ├── analytics/
│   │   │   └── repositories/
│   │   │       └── sqlalchemy_analytics_repository.py  # IAnalyticsRepository impl
│   │   ├── usage/
│   │   │   └── repositories/
│   │   │       └── sqlalchemy_token_usage_repository.py  # ITokenUsageRepository impl
│   │   ├── services/
│   │   │   ├── langchain_agent_service.py  # LangChainAgentService (REAL)
│   │   │   ├── openai_llm_service.py       # OpenAILLMService (REAL)
│   │   │   ├── anthropic_llm_service.py    # AnthropicLLMService (REAL)
│   │   │   ├── openai_tagging_service.py   # OpenAITaggingService (REAL)
│   │   │   ├── redis_event_bus.py          # RedisEventBus (REAL)
│   │   │   ├── profile_service.py          # ProfileService (REAL)
│   │   │   ├── mock_user_knowledge_service.py       # MockUserKnowledgeService (STUB)
│   │   │   └── mock_similarity_search_service.py    # MockSimilaritySearchService (STUB)
│   │   ├── external/
│   │   │   └── llm_providers.py      # LLMProviderFactory (health checks, registration)
│   │   └── observability/
│   │       └── cloudwatch_logger.py  # CloudWatch logging integration
│   │
│   └── presentation/                 # Layer 4: HTTP routing, middleware, auth
│       ├── dependencies.py           # JWT decode, service getters (get_current_user_id, etc.)
│       └── api/
│           ├── main.py               # create_application() factory
│           ├── routers/              # 10 API endpoint routers
│           │   ├── __init__.py       # Imports all routers for main.py
│           │   ├── deps.py           # Route dependencies (get_container, get_current_user_id)
│           │   ├── health.py         # GET /health (no auth)
│           │   ├── auth.py           # POST /auth/login, /auth/register
│           │   ├── chat.py           # POST /chat (MAIN: send message to agent)
│           │   ├── records.py        # /emotional_records (CRUD)
│           │   ├── breathing.py      # /breathing_* (patterns, sessions)
│           │   ├── usage.py          # GET /usage (token budget)
│           │   ├── profile.py        # GET/PUT /profile
│           │   ├── suggestions.py    # /suggestions (daily wellness)
│           │   ├── data.py           # /data (export)
│           │   ├── ws.py             # ws:// (WebSocket calendar)
│           │   ├── mobile_logs.py    # POST /mobile_logs (error tracking)
│           │   └── dev_seed.py       # /dev_seed (dev-only test data)
│           ├── middleware/
│           │   ├── __init__.py
│           │   ├── error_handling.py # ErrorHandlingMiddleware (try/catch, CloudWatch)
│           │   ├── logging.py        # LoggingMiddleware (request/response logging)
│           │   └── rate_limiting.py  # RateLimitingMiddleware (requests/minute)
│           ├── validators/
│           │   └── data_validators.py # Request data validation helpers
│           └── events/
│               └── manager.py        # Event manager for pub/sub coordination
```

## Directory Purposes

**`src/domain/`:**
- Purpose: Core business logic isolated from frameworks
- Contains: Entities (User, Conversation), value objects, interfaces (repository contracts), domain events
- Key files: `entities/user.py` (User entity), `*/interfaces.py` (repository abstractions)
- No imports from FastAPI, SQLAlchemy, or external libraries

**`src/application/`:**
- Purpose: Business orchestration and use case implementation
- Contains: Use cases, service interfaces, DTOs, exceptions
- Key files: `chat/use_cases/agent_chat_use_case.py` (main flow), `services/*.py` (interface definitions), `dtos/*.py` (API contracts)

**`src/infrastructure/`:**
- Purpose: Technical implementations, persistence, external integrations
- Contains: SQLAlchemy repos, LangChain service, OpenAI client, Redis, settings
- Key files: `container.py` (DI wiring), `database/models.py` (ORM), `services/*.py` (implementations), `config/settings.py` (env config)

**`src/presentation/`:**
- Purpose: HTTP handling, routing, authentication, middleware
- Contains: FastAPI routers, middleware, dependencies, JWT logic
- Key files: `api/routers/*.py` (10 endpoint handlers), `dependencies.py` (auth + service injection), `api/middleware/*.py` (cross-cutting)

---

## Key File Locations

**Entry Points:**
- `main.py` (project root): FastAPI app creation and startup/shutdown lifecycle
- `src/presentation/api/main.py`: create_application() function (called by main.py)

**Configuration:**
- `src/infrastructure/config/settings.py`: All env vars via Pydantic Settings
- `docker-compose.yml`: Local dev services (postgres, redis)
- `pyproject.toml`: Dependencies, poetry config

**Core Business Logic:**
- `src/domain/entities/user.py`: User entity with domain methods
- `src/application/chat/use_cases/agent_chat_use_case.py`: Main chat flow (~200 lines)
- `src/application/usage/use_cases/get_monthly_usage_use_case.py`: Simple usage query (16 lines)

**Persistence:**
- `src/infrastructure/database/connection.py`: Async SQLAlchemy session factory
- `src/infrastructure/database/models.py`: All ORM models (User, Conversation, EmotionalRecord, etc.)
- `src/infrastructure/repositories/sqlalchemy_user_repository.py`: User repo implementation
- `alembic/versions/001_initial_schema.py`: Single migration with all schema

**AI Services:**
- `src/infrastructure/services/langchain_agent_service.py`: LangChain agent with GPT-4
- `src/infrastructure/services/openai_tagging_service.py`: Semantic tagging (GPT-4o-mini)
- `src/infrastructure/services/openai_llm_service.py`: OpenAI wrapper
- `src/infrastructure/services/anthropic_llm_service.py`: Anthropic Claude wrapper

**Dependency Injection:**
- `src/infrastructure/container.py`: ApplicationContainer (composition root) ← **START HERE FOR DI**
- `src/presentation/dependencies.py`: Service accessors (get_current_user_id, etc.)
- `src/presentation/api/routers/deps.py`: Router-specific dependencies

**API Endpoints (Routers):**
- `src/presentation/api/routers/__init__.py`: Imports all routers
- `src/presentation/api/routers/chat.py`: POST /chat (primary endpoint)
- `src/presentation/api/routers/auth.py`: Login/register
- `src/presentation/api/routers/health.py`: GET /health
- `src/presentation/api/routers/records.py`: Emotional record CRUD
- `src/presentation/api/routers/breathing.py`: Breathing exercises
- `src/presentation/api/routers/usage.py`: Token budget
- `src/presentation/api/routers/profile.py`: User profile
- `src/presentation/api/routers/ws.py`: WebSocket real-time updates

**Testing:**
- `tests/test_integration.py`: Integration tests (use cases + real repos)
- `tests/test_database_integrations.py`: Database-specific tests

---

## Naming Conventions

**Files:**
- Domain: singular (`user.py`, `conversation.py`), no prefix
- Application use cases: `*_use_case.py` (e.g., `agent_chat_use_case.py`)
- Infrastructure: `sqlalchemy_*_repository.py`, `*_service.py`
- Routers: `{feature}.py` (e.g., `chat.py`, `auth.py`)
- Tests: `test_{module}.py` (e.g., `test_agent_chat_use_case.py`)

**Directories:**
- Feature-based grouping: `domain/{feature}/`, `infrastructure/{feature}/repositories/`
- Service layer: `services/` for implementations, `{service}_service.py` convention
- Routers: `api/routers/` all in one directory

**Classes:**
- Entities: PascalCase no suffix (User, Conversation)
- Value Objects: PascalCase no suffix (UserProfile, AgentPersonality)
- Repository interfaces: IPrefixed (IUserRepository, IEmotionalRecordRepository)
- Service interfaces: IPrefixed (IAgentService, ITaggingService)
- Implementations: DescriptivePrefix (SqlAlchemyUserRepository, LangChainAgentService)
- Use cases: PascalCase + "UseCase" (AgentChatUseCase, GetMonthlyUsageUseCase)
- Models (ORM): PascalCase + "Model" (UserModel, ConversationModel)

**Functions/Methods:**
- camelCase not used; snake_case throughout
- Route handlers: action verb + object (e.g., `chat_with_agent()`, `get_monthly_usage()`)
- Interfaces: async methods prefixed with `async def` (e.g., `async def send_message()`)
- Mappers: `_model_to_entity()`, `_entity_to_model()` (private convention)

---

## Where to Add New Code

**New Feature (Example: Custom Emotions CRUD):**
- Domain entity: `src/domain/custom_emotions/entities.py` (CustomEmotion)
- Repository interface: `src/domain/custom_emotions/interfaces.py` (ICustomEmotionRepository)
- Repository implementation: `src/infrastructure/custom_emotions/repositories/sqlalchemy_custom_emotion_repository.py`
- Use case: `src/application/custom_emotions/use_cases/` (e.g., GetCustomEmotionsUseCase)
- Router: `src/presentation/api/routers/custom_emotions.py`
- Register router in: `src/presentation/api/routers/__init__.py` and `main.py` include_router()
- Register service in: `src/infrastructure/container.py`

**New Repository:**
1. Define interface in `src/domain/{feature}/interfaces.py`
2. Implement in `src/infrastructure/{feature}/repositories/sqlalchemy_{feature}_repository.py`
3. Register in `src/infrastructure/container.py` (lines 110-117)
4. Inject into use cases or services

**New Service (Real Implementation):**
1. Define interface in `src/application/services/{service}_service.py`
2. Implement in `src/infrastructure/services/{service}_service.py`
3. Register in `src/infrastructure/container.py` (lines 118-161)
4. Inject into use cases via constructor

**New Middleware:**
1. Create in `src/presentation/api/middleware/{middleware_name}.py`
2. Inherit from `BaseHTTPMiddleware`
3. Add to app in `src/presentation/api/main.py` via `app.add_middleware()`

**New Route:**
1. Create or edit router in `src/presentation/api/routers/{feature}.py`
2. Inject dependencies: `Depends(get_current_user_id)`, `Depends(get_container)`
3. Call use case: `container.{service_name}.execute(...)`
4. Map response to DTO (Pydantic model)
5. Register router in `src/presentation/api/routers/__init__.py` and `main.py`

**New Validator:**
1. Add to `src/presentation/api/validators/data_validators.py`
2. Reference in router endpoint

**Database Migration:**
1. Edit ORM models in `src/infrastructure/database/models.py`
2. Run: `alembic revision --autogenerate -m "describe_change"`
3. Verify generated migration in `alembic/versions/`
4. Run: `alembic upgrade head`

---

## Special Directories

**`.planning/codebase/`:**
- Purpose: Generated architecture documentation
- Generated: Yes (by /gsd:map-codebase)
- Committed: Yes (documentation for future Claude instances)
- Contains: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

**`alembic/`:**
- Purpose: Database migration tracking and versioning
- Generated: Partially (env.py is template, versions/ generated)
- Committed: Yes (migrations are history)
- Key: `versions/001_initial_schema.py` is the ONLY migration file (never edit it, create new revisions)

**`migrations/`:**
- Purpose: Alembic configuration environment
- Generated: No (part of Alembic setup)
- Committed: Yes

**`tests/`:**
- Purpose: Integration tests (no unit tests yet)
- Generated: No
- Committed: Yes
- Run: `pytest test_integration.py -v`

**`.venv/` (not committed):**
- Purpose: Python virtual environment
- Generated: Yes (poetry install)
- Committed: No (in .gitignore)

---

*Structure analysis: 2026-03-19*
