# Architecture

**Analysis Date:** 2026-03-19

## Pattern Overview

**Overall:** Clean Architecture (4-layer) with Dependency Injection (DI) Composition Root

**Key Characteristics:**
- Strict separation of concerns across domain, application, infrastructure, and presentation layers
- Dependency rule: Domain ← Application ← Infrastructure ← Presentation (never reversed)
- All business logic isolated in domain layer (no framework imports permitted)
- Service interfaces defined in application layer; implementations in infrastructure
- Centralized composition root via `ApplicationContainer` for wiring all dependencies
- Async-first design with asyncpg for PostgreSQL and async event bus via Redis

## Layers

**Domain Layer:**
- Purpose: Pure business logic, entities, value objects, and repository interfaces
- Location: `src/domain/`
- Contains: User entity, chat entities, emotional records, breathing sessions, value objects (AgentPersonality, UserProfile), domain events
- Depends on: Nothing (zero external dependencies)
- Used by: Application layer only
- Key files: `src/domain/entities/user.py`, `src/domain/value_objects/`, `src/domain/{chat,breathing,records,analytics,events,users,usage}/interfaces.py`

**Application Layer:**
- Purpose: Use cases, service interfaces, DTOs, and orchestration of domain logic
- Location: `src/application/`
- Contains: Use cases (AgentChatUseCase, GetMonthlyUsageUseCase), service interfaces (IAgentService, IEventBus, ITaggingService), DTOs for request/response contracts, exception hierarchy
- Depends on: Domain layer only
- Used by: Infrastructure and presentation layers
- Key files: `src/application/chat/use_cases/agent_chat_use_case.py`, `src/application/dtos/chat_dtos.py`, `src/application/exceptions.py`, `src/application/services/{agent_service.py, event_bus.py, tagging_service.py}`

**Infrastructure Layer:**
- Purpose: Concrete implementations of interfaces: SQLAlchemy repositories, external service clients, Redis bus, LangChain agent service
- Location: `src/infrastructure/`
- Contains: SQLAlchemy models and repositories (user, conversation, emotional records, breathing, analytics, events, usage), LangChain agent service, OpenAI/Anthropic LLM services, Redis event bus, profile service, database connection pool, configuration loading
- Depends on: Domain and application layers
- Used by: Presentation layer (via container)
- Key files: `src/infrastructure/container.py` (DI wiring), `src/infrastructure/database/models.py`, `src/infrastructure/repositories/`, `src/infrastructure/services/{langchain_agent_service.py, openai_tagging_service.py, redis_event_bus.py}`

**Presentation Layer:**
- Purpose: HTTP API endpoints, middleware, validators, WebSocket handlers
- Location: `src/presentation/api/`
- Contains: FastAPI routers (11 routers: auth, chat, breathing, records, usage, profile, data, health, suggestions, ws, dev_seed), middleware (error handling, logging, rate limiting), request validators, JWT authentication, WebSocket connection management
- Depends on: Application and infrastructure layers
- Used by: FastAPI application entry point
- Key files: `src/presentation/api/routers/`, `src/presentation/api/middleware/`, `src/presentation/api/main.py` (app factory)

## Data Flow

**Chat Message Flow (Core Use Case):**

1. **Request Entry** → `POST /v1/api/chat` (FastAPI router: `src/presentation/api/routers/chat.py`)
2. **Authentication** → JWT token validated via `get_current_user_id` dependency (`src/presentation/api/routers/deps.py`)
3. **Dependency Injection** → Container retrieved via `get_container` dependency (contains all wired services)
4. **Request Validation** → `ChatApiRequest` validated against Pydantic schema
5. **Use Case Invocation** → `AgentChatUseCase.execute()` called with user_id, agent_type, message
6. **Domain Logic**:
   - Retrieve user via `user_repository.get_by_id()` (SQLAlchemy repository)
   - Fetch user profile and agent preferences from database
7. **External LLM Call** → `agent_service.send_message()` (LangChain + OpenAI/Anthropic)
   - User history retrieved from `conversation_repository`
   - AI generates response using user context and conversation memory
8. **Semantic Tagging** → `tagging_service.tag_response()` (GPT-4o-mini) [async best-effort]
   - Response tagged with emotion, intent, severity
   - Token usage logged to `token_usage_repo`
9. **Suggestion Persistence** → If suggestions included, upsert to `DailySuggestionModel` (best-effort)
10. **Event Publishing** → Domain events queued to Redis via `event_bus` (async)
11. **Response Serialization** → DTO converted to `ChatApiResponse`
12. **HTTP Response** → 200 OK with `{ message, agent_type, suggestions, timestamp }`

**State Management:**
- **User State**: Stored in PostgreSQL, retrieved per-request via `IUserRepository`
- **Conversation History**: Stored in `conversations` table, retrieved via `IAgentConversationRepository`
- **Session State**: In-memory agent context per conversation (LangChain manages)
- **Event Queue**: Redis pub/sub for asynchronous event propagation
- **Token Usage**: Per-user monthly tracking in `token_usage` table via `ITokenUsageRepository`

## Key Abstractions

**Repository Pattern:**
- Purpose: Abstract database access behind interfaces defined in domain
- Examples: `IUserRepository`, `IAgentConversationRepository`, `IEmotionalRecordRepository`, `IBreathingSessionRepository`, `IEventRepository`, `IAnalyticsRepository`, `ITokenUsageRepository`
- Pattern: One interface per domain concept; implementations use SQLAlchemy ORM
- Location: `src/domain/{users,chat,records,breathing,events,analytics,usage}/interfaces.py` → `src/infrastructure/{repositories,conversations,records,breathing,events,analytics,usage}/repositories/`

**Service Pattern:**
- Purpose: Complex operations that don't fit repositories (e.g., external service calls, multi-step orchestration)
- Examples: `IAgentService` (LLM conversation), `IEventBus` (event publishing), `ITaggingService` (semantic tagging), `IProfileService` (user profiling), `IUserKnowledgeService` (user context extraction)
- Pattern: Interface in application layer, implementation in infrastructure
- Location: `src/application/services/` → `src/infrastructure/services/`

**Use Case Pattern:**
- Purpose: Single business transaction orchestration
- Example: `AgentChatUseCase` coordinates user lookup, agent service call, tagging, token logging, suggestion persistence
- Pattern: Single `execute()` method; constructor dependency injection for all repos and services
- Location: `src/application/chat/use_cases/agent_chat_use_case.py`

**DTO Pattern:**
- Purpose: Type-safe request/response contracts at API boundaries
- Examples: `ChatRequest`, `ChatResponse`, `UserRegistrationRequest`, `TokenResponse`, `ConversationHistoryResponse`
- Pattern: Frozen dataclasses with `__post_init__` validation; `to_dict()` for serialization
- Location: `src/application/dtos/chat_dtos.py`, `src/application/dtos/profile_dtos.py`

**Value Object Pattern:**
- Purpose: Immutable domain concepts with internal consistency rules
- Examples: `AgentPersonality` (enum-like with validation), `UserProfile` (complex user data structure)
- Pattern: Dataclasses with validation methods; used within domain entities
- Location: `src/domain/value_objects/agent_personality.py`, `src/domain/value_objects/user_profile.py`

## Entry Points

**HTTP Server:**
- Location: `main.py` (project root)
- Triggers: `python -m uvicorn main:app --reload` or systemd service
- Responsibilities: Imports app factory, runs uvicorn with config

**App Factory:**
- Location: `src/presentation/api/main.py` function `create_application()`
- Triggers: Called by lifespan context manager in `main.py`
- Responsibilities: Creates FastAPI instance, wires middleware, mounts routers, sets exception handlers

**Container Initialization:**
- Location: `src/infrastructure/container.py` function `initialize_container()`
- Triggers: Called during app startup via lifespan context manager
- Responsibilities: Orchestrates database connection, creates all repositories/services, wires entire DI container

**Router Entry Points (Protected Routes):**
- `POST /v1/api/chat` → `chat.py:chat_with_agent()` (requires JWT)
- `POST /v1/api/auth/login` → `auth.py:login()` (public)
- `POST /v1/api/auth/register` → `auth.py:register()` (public)
- `GET /v1/api/profile` → `profile.py:get_profile()` (requires JWT)
- `GET /v1/api/emotional_records` → `records.py:get_records()` (requires JWT)
- `POST /v1/api/breathing_sessions` → `breathing.py:start_session()` (requires JWT)
- `GET /health` → `health.py:health_check()` (public)
- `WS /ws/...` → `ws.py:websocket_endpoint()` (JWT via URL param)

## Error Handling

**Strategy:** Layered exception hierarchy with centralized middleware catch

**Patterns:**
- Domain → Application exception types raised from use cases (UserNotFoundException, AgentServiceException, etc.)
- Application exceptions caught by `ErrorHandlingMiddleware` in `src/presentation/api/middleware/error_handling.py`
- HTTPExceptions from Pydantic validation caught by FastAPI's built-in handler
- Unhandled exceptions caught by general exception handler → 500 response
- All errors logged to CloudWatch when mobile_logs_enabled (best-effort)
- Location: `src/application/exceptions.py` (exception hierarchy), `src/presentation/api/middleware/error_handling.py` (centralized handling), `main.py` (per-exception handlers)

## Cross-Cutting Concerns

**Logging:**
- Framework: Python standard logging module
- Configuration: `src/infrastructure/config/settings.py` controls log level per environment
- Approach: Every router endpoint and use case logs entry/exit; middleware logs all requests; exceptions logged with traceback

**Validation:**
- Request-level: Pydantic models in routers auto-validate against schema
- DTO-level: Dataclass `__post_init__` methods validate semantics (e.g., intensity 1-10, valid email)
- Domain-level: Entity methods validate business rules (e.g., User.update_profile, User.change_agent_personality)

**Authentication:**
- Method: JWT HS256 (symmetric key)
- Token extraction: `HTTPBearer` dependency in `src/presentation/api/routers/deps.py`
- Validation: Centralized in `src/presentation/dependencies.py:get_current_user_id()`
- Fallback: Hardcoded UUID fallback in `deps.py` (security debt - see CONCERNS.md)

**Observability:**
- Health checks: `GET /health` returns component status (database, LLM providers, event bus, agent service)
- Container method: `ApplicationContainer.health_check()` probes all components
- Metrics endpoint: Not yet exposed (metrics collected but not public)
- CloudWatch integration: Optional mobile error logging in error handler

**Rate Limiting:**
- Configuration: `settings.rate_limit_requests` (requests per minute)
- Implementation: `RateLimitingMiddleware` in `src/presentation/api/middleware/rate_limiting.py`
- Applied: All non-health endpoints when enabled

---

*Architecture analysis: 2026-03-19*
