# Codebase Structure

**Analysis Date:** 2026-03-19

## Directory Layout

```
emotionai-api/
├── main.py                           # Entry point: uvicorn runner + app factory caller
├── docker-compose.yml                # Local dev: postgres, redis, api containers
├── pyproject.toml                    # Project metadata, dependencies
├── alembic.ini                       # Database migration configuration
├── deploy/                           # Deployment configuration (not code)
│   ├── ec2/                         # EC2 instance setup scripts
│   └── nginx/                       # Nginx reverse proxy config
├── migrations/                       # Alembic database migrations
│   └── versions/                     # Migration files (001_initial_schema.py only)
├── scripts/                          # Utility scripts (not used; see dev scripts elsewhere)
├── tests/                            # Test suite
│   ├── application/                 # Application layer tests
│   └── domain/                      # Domain layer tests
└── src/                              # Main application code (4-layer architecture)
    ├── __init__.py
    ├── domain/                       # Layer 1: Domain (business logic, no frameworks)
    │   ├── analytics/
    │   │   └── interfaces.py         # IAnalyticsRepository interface
    │   ├── breathing/
    │   │   └── interfaces.py         # IBreathingSessionRepository interface
    │   ├── chat/
    │   │   ├── entities.py           # Chat-specific entities
    │   │   └── interfaces.py         # IAgentConversationRepository interface
    │   ├── entities/
    │   │   └── user.py               # User domain entity with business methods
    │   ├── events/
    │   │   ├── domain_events.py      # UserCreatedEvent, UserProfileUpdatedEvent, etc.
    │   │   └── interfaces.py         # IEventRepository interface
    │   ├── records/
    │   │   └── interfaces.py         # IEmotionalRecordRepository interface
    │   ├── repositories/             # Marker directory (interfaces in feature dirs)
    │   │   └── __init__.py
    │   ├── usage/
    │   │   └── interfaces.py         # ITokenUsageRepository interface
    │   ├── users/
    │   │   └── interfaces.py         # IUserRepository interface
    │   └── value_objects/
    │       ├── agent_personality.py  # AgentPersonality enum-like value object
    │       └── user_profile.py       # UserProfile complex value object
    │
    ├── application/                  # Layer 2: Application (use cases, DTOs, service interfaces)
    │   ├── chat/
    │   │   └── use_cases/
    │   │       └── agent_chat_use_case.py  # Core chat orchestration use case
    │   ├── dtos/                      # Data Transfer Objects for API contracts
    │   │   ├── chat_dtos.py          # ChatRequest, ChatResponse, etc.
    │   │   └── profile_dtos.py       # User profile DTOs
    │   ├── exceptions.py              # ApplicationException hierarchy
    │   ├── services/                  # Service interfaces (implementations in infrastructure)
    │   │   ├── agent_service.py      # IAgentService interface
    │   │   ├── event_bus.py          # IEventBus interface
    │   │   ├── llm_service.py        # ILLMService interface
    │   │   ├── profile_service.py    # IProfileService interface
    │   │   ├── similarity_search_service.py  # ISimilaritySearchService interface
    │   │   ├── tagging_service.py    # ITaggingService interface
    │   │   └── user_knowledge_service.py    # IUserKnowledgeService interface
    │   ├── tagging/
    │   │   └── services/
    │   │       └── tagging_service.py  # Tagging service interface (mirrored in infrastructure)
    │   └── usage/
    │       └── use_cases/
    │           └── get_monthly_usage_use_case.py  # Token usage retrieval use case
    │
    ├── infrastructure/               # Layer 3: Infrastructure (implementations, external services, database)
    │   ├── analytics/
    │   │   └── repositories/
    │   │       └── sqlalchemy_analytics_repository.py  # Analytics data access
    │   ├── breathing/
    │   │   └── repositories/
    │   │       └── sqlalchemy_breathing_repository.py  # Breathing session persistence
    │   ├── config/
    │   │   └── settings.py           # Pydantic Settings: loads environment config
    │   ├── container.py              # Dependency Injection Composition Root (ApplicationContainer)
    │   ├── conversations/
    │   │   └── repositories/
    │   │       └── sqlalchemy_conversation_repository.py  # Conversation history persistence
    │   ├── database/
    │   │   ├── connection.py         # DatabaseConnection: asyncpg pool, session factory
    │   │   └── models.py             # SQLAlchemy ORM models (UserModel, ConversationModel, etc.)
    │   ├── events/
    │   │   └── repositories/
    │   │       └── sqlalchemy_event_repository.py  # Domain event persistence
    │   ├── external/
    │   │   └── llm_providers.py      # LLMProviderFactory: abstraction over OpenAI/Anthropic
    │   ├── observability/
    │   │   └── cloudwatch_logger.py  # CloudWatch log event publishing
    │   ├── records/
    │   │   └── repositories/
    │   │       └── sqlalchemy_emotional_repository.py  # Emotional record persistence
    │   ├── repositories/             # Legacy location (being moved to feature dirs)
    │   │   └── sqlalchemy_user_repository.py  # User persistence
    │   ├── services/
    │   │   ├── anthropic_llm_service.py  # Anthropic Claude LLM implementation
    │   │   ├── langchain_agent_service.py  # LangChain + LLM orchestration (core AI service)
    │   │   ├── mock_similarity_search_service.py  # Stub similarity search (TODO: implement)
    │   │   ├── mock_user_knowledge_service.py    # Stub user knowledge extraction (TODO: implement)
    │   │   ├── openai_llm_service.py  # OpenAI LLM implementation
    │   │   ├── openai_tagging_service.py  # Semantic tagging via GPT-4o-mini
    │   │   ├── profile_service.py     # User profile computation service
    │   │   └── redis_event_bus.py    # Redis pub/sub event bus implementation
    │   ├── tagging/
    │   │   └── services/
    │   │       └── openai_tagging_service.py  # (alias to main tagging service)
    │   └── usage/
    │       └── repositories/
    │           └── sqlalchemy_token_usage_repository.py  # Token usage tracking
    │
    └── presentation/                 # Layer 4: Presentation (HTTP API, WebSocket, middleware)
        └── api/
            ├── events/
            │   └── manager.py        # Event handler registration
            ├── middleware/           # Request/response middleware
            │   ├── error_handling.py  # Error catching, logging, response formatting
            │   ├── logging.py        # Request/response logging
            │   └── rate_limiting.py  # Rate limiter per user/IP
            ├── routers/              # FastAPI routers (mounted in main.py)
            │   ├── auth.py           # POST /v1/api/auth/login, /register
            │   ├── breathing.py      # POST/GET /v1/api/breathing_*
            │   ├── chat.py           # POST /v1/api/chat (core endpoint)
            │   ├── data.py           # GET /v1/api/data/* (data export)
            │   ├── deps.py           # Dependency providers: get_container, get_current_user_id
            │   ├── dev_seed.py       # GET /v1/api/seed/* (dev-only test data)
            │   ├── health.py         # GET /health (public, no auth)
            │   ├── mobile_logs.py    # POST /v1/api/mobile_logs (client error logging)
            │   ├── profile.py        # GET/PUT /v1/api/profile
            │   ├── records.py        # POST/GET /v1/api/emotional_records
            │   ├── suggestions.py    # GET /v1/api/suggestions (follow-up suggestions)
            │   ├── usage.py          # GET /v1/api/usage (token budget)
            │   └── ws.py             # WS /ws/* (WebSocket calendar sync)
            ├── validators/
            │   └── data_validators.py  # Custom request validators
            └── main.py               # create_application() factory, exception handlers
        └── dependencies.py           # JWT token validation (get_current_user_id)
```

## Directory Purposes

**`src/domain/`:**
- Purpose: Pure domain logic isolated from all frameworks
- Contains: Entities (User), value objects (AgentPersonality, UserProfile), repository interfaces, domain events
- Key files: `entities/user.py`, `value_objects/agent_personality.py`, `value_objects/user_profile.py`, `*/interfaces.py`

**`src/application/`:**
- Purpose: Use case orchestration and service interfaces
- Contains: Use cases, DTOs (request/response schemas), exception hierarchy, service interfaces
- Key files: `chat/use_cases/agent_chat_use_case.py`, `dtos/chat_dtos.py`, `exceptions.py`, `services/*.py`

**`src/infrastructure/`:**
- Purpose: Concrete implementations of repositories and services, database, external integrations
- Contains: SQLAlchemy models and repositories, LangChain agent service, LLM clients (OpenAI/Anthropic), Redis event bus, settings loader
- Key files: `container.py`, `database/models.py`, `database/connection.py`, `services/langchain_agent_service.py`, `config/settings.py`

**`src/presentation/api/`:**
- Purpose: HTTP endpoints and WebSocket handlers
- Contains: FastAPI routers (11 total), middleware, request/response handling
- Key files: `routers/chat.py`, `routers/auth.py`, `main.py`, `middleware/error_handling.py`, `routers/deps.py`

**`migrations/versions/`:**
- Purpose: Alembic database schema migrations
- Contains: Single migration file `001_initial_schema.py` (all schema in one file; never edit directly)
- Never edit: Always create new revisions via `alembic revision --autogenerate -m "..."`

**`tests/`:**
- Purpose: Test suite (integration and domain tests)
- Contains: Test fixtures, mocks, integration tests
- Currently: No comprehensive unit tests; integration tests cover main flows

**`deploy/`:**
- Purpose: Deployment configuration (non-code)
- Contains: EC2 setup scripts, Nginx reverse proxy config, systemd service files
- Not code: Configuration and infrastructure setup

## Key File Locations

**Entry Points:**
- `main.py`: Server entry point (runs uvicorn)
- `src/presentation/api/main.py:create_application()`: FastAPI app factory
- `src/infrastructure/container.py:initialize_container()`: DI container initialization

**Configuration:**
- `src/infrastructure/config/settings.py`: All environment variables via Pydantic Settings
- `alembic.ini`: Database migration configuration
- `docker-compose.yml`: Local dev environment

**Core Logic:**
- `src/domain/entities/user.py`: User domain entity
- `src/application/chat/use_cases/agent_chat_use_case.py`: Main chat orchestration
- `src/infrastructure/services/langchain_agent_service.py`: LangChain + LLM agent
- `src/infrastructure/database/models.py`: SQLAlchemy ORM models

**Testing:**
- `tests/application/`: Application layer tests
- `tests/domain/`: Domain layer tests

## Naming Conventions

**Files:**
- Service implementations: `{service_type}_service.py` (e.g., `langchain_agent_service.py`, `redis_event_bus.py`)
- Repository implementations: `sqlalchemy_{entity}_repository.py` (e.g., `sqlalchemy_user_repository.py`)
- Routers: `{feature}.py` (e.g., `chat.py`, `auth.py`)
- Models: `{entity_name}_model.py` (e.g., `user.py` contains UserModel, ConversationModel)
- DTOs: `{feature}_dtos.py` (e.g., `chat_dtos.py`)
- Middleware: `{concern}.py` (e.g., `error_handling.py`, `logging.py`)

**Directories:**
- Feature-scoped: `src/domain/{feature}/`, `src/infrastructure/{feature}/` (e.g., `chat/`, `breathing/`, `records/`)
- Layer-organized: `src/{layer}/{concern}/` (e.g., `src/presentation/api/routers/`)
- Type-specific: `repositories/`, `services/`, `use_cases/` (group by responsibility)

## Where to Add New Code

**New Feature (e.g., Journaling):**

1. **Domain** (`src/domain/journaling/`):
   - Create `interfaces.py` with `IJournalEntryRepository` interface
   - Create `entities/` or `value_objects/` if modeling new concepts
   - Create `domain_events.py` if events need publishing

2. **Application** (`src/application/journaling/`):
   - Create `use_cases/create_journal_entry_use_case.py` (orchestrates domain logic)
   - Add DTOs to `src/application/dtos/journal_dtos.py`
   - Add service interfaces to `src/application/services/` if needed

3. **Infrastructure** (`src/infrastructure/journaling/`):
   - Create `repositories/sqlalchemy_journal_repository.py` implementing `IJournalEntryRepository`
   - Add SQLAlchemy model to `src/infrastructure/database/models.py`
   - Register in `src/infrastructure/container.py` (wire repository into container)

4. **Presentation** (`src/presentation/api/routers/`):
   - Create `journaling.py` router with endpoints
   - Inject use case and repositories via `get_container()` dependency
   - Mount router in `src/presentation/api/main.py`: `app.include_router(journaling_router, prefix="/v1/api", tags=["Journaling"], dependencies=[Depends(get_current_user_id)])`

5. **Database**:
   - Add model to `src/infrastructure/database/models.py`
   - Create migration: `alembic revision --autogenerate -m "add_journaling_tables"`
   - Apply: `alembic upgrade head`

**New Component/Module:**
- Implementation: `src/{layer}/{feature}/` (follow feature naming)
- Tests: `tests/{layer}/{feature}/test_{feature}.py`
- Register in `src/infrastructure/container.py` if a service

**Utilities:**
- Shared helpers: `src/application/services/` (service-like) or domain-level (value objects)
- Validation: `src/presentation/api/validators/`
- Configuration: `src/infrastructure/config/`

## Special Directories

**`migrations/versions/`:**
- Purpose: Alembic database schema versions
- Generated: Yes (created by `alembic revision --autogenerate`)
- Committed: Yes (track migrations in version control)
- Rules: Never hand-edit `001_initial_schema.py`; create new revisions for changes

**`.venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (created by `python -m venv .venv`)
- Committed: No (gitignored)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (auto-created by Python interpreter)
- Committed: No (gitignored)

**`src/infrastructure/database/models.py`:**
- Purpose: Single SQLAlchemy model file (all ORM models in one place)
- Why: Simpler relationship management; all tables visible at a glance
- Relationship: Maps to domain entities but includes persistence-specific fields
- Example: `UserModel` includes `therapy_context` (JSONB) for AI state (not in domain User entity)

---

*Structure analysis: 2026-03-19*
