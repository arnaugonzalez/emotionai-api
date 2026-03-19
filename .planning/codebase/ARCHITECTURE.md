# Architecture

**Analysis Date:** 2026-03-19

## Pattern Overview

**Overall:** Clean Architecture with explicit layer separation (Domain → Application → Infrastructure → Presentation)

**Key Characteristics:**
- Strict dependency direction: business logic (domain) never imports framework code
- Composition root pattern via `ApplicationContainer` for centralized DI wiring
- Service-oriented application layer with use cases orchestrating repositories and services
- SQLAlchemy ORM for persistence with explicit mapping to domain entities
- LangChain agent-based AI integration for therapeutic conversation
- Event-driven architecture via Redis pub/sub for async operations

---

## Layers

**Domain Layer:**
- Purpose: Pure business logic and entities with no framework imports
- Location: `src/domain/`
- Contains: entities (`User`, conversation state), value objects (`AgentPersonality`, `UserProfile`), interfaces (repository contracts), domain events
- Depends on: Nothing (no external dependencies)
- Used by: Application layer for use case implementation

**Application Layer:**
- Purpose: Business rules orchestration, use cases, DTOs, service interfaces
- Location: `src/application/`
- Contains: use cases (`AgentChatUseCase`, `GetMonthlyUsageUseCase`), service interfaces (`IAgentService`, `ITaggingService`), DTOs for API contracts, exception definitions
- Depends on: Domain layer only
- Used by: Infrastructure (implementations) and Presentation (dependency injection)

**Infrastructure Layer:**
- Purpose: Technical implementation, external integrations, data persistence
- Location: `src/infrastructure/`
- Contains: SQLAlchemy repositories, LangChain agent service, OpenAI/Anthropic LLM wrappers, Redis event bus, database connection pool, configuration
- Depends on: Application layer (implements interfaces), Domain layer (maps to/from entities)
- Used by: Presentation layer via injected services from container

**Presentation Layer:**
- Purpose: HTTP routing, request/response handling, middleware, authentication
- Location: `src/presentation/`
- Contains: FastAPI routers (10 endpoints), JWT authentication logic, middleware (logging, error handling, rate limiting), request validators
- Depends on: Application layer (uses services), Infrastructure layer (uses container)
- Used by: FastAPI application in `main.py`

---

## Data Flow

**Typical Request Flow (Chat Message Example):**

1. **Entry**: `POST /v1/api/chat` received by FastAPI router at `src/presentation/api/routers/chat.py`
2. **Auth**: Middleware and `get_current_user_id()` from `src/presentation/dependencies.py` extracts/validates JWT token
3. **Validation**: Request payload validated via Pydantic `ChatApiRequest` model
4. **Container Access**: Router retrieves `ApplicationContainer` from `app.state.container` via dependency injection
5. **Use Case Execution**: Router calls `container.agent_chat_use_case.execute(user_id, agent_type, message, context)`
6. **Repository Access**: Use case in `src/application/chat/use_cases/agent_chat_use_case.py` queries repositories:
   - `user_repository.get_by_id(user_id)` → fetch user entity
   - `conversation_repository.save()` → persist conversation
   - `emotional_repository.save()` → track emotional state
7. **Service Orchestration**: Use case calls:
   - `agent_service.send_message()` → LangChain agent with GPT-4 prompt
   - `tagging_service.tag_response()` → semantic tagging via GPT-4o-mini
   - `user_knowledge_service.update_profile()` → mock (stub) profile update
8. **Response Mapping**: Use case returns domain response object
9. **DTO Conversion**: Router converts domain response to API response (`ChatApiResponse`)
10. **Return**: FastAPI serializes response to JSON, status 200

**State Management:**
- User state persisted in PostgreSQL (`users` table)
- Conversation history in `conversation_messages` table
- Emotional records indexed for pattern analysis
- Redis event bus queues async tagging operations
- No in-memory state (stateless design)

---

## Key Abstractions

**ApplicationContainer:**
- Purpose: Dependency injection registry and composition root
- Examples: `src/infrastructure/container.py` lines 56-203
- Pattern: Dataclass with factory method `ApplicationContainer.create()` that wires all dependencies in dependency order
- Initialization: At app startup via `lifespan()` context manager in `main.py` lines 50-81
- Lifecycle: Stored in `app.state.container` for access via FastAPI dependency injection

**IUserRepository (Interface):**
- Purpose: Abstract contract for user persistence operations
- Examples: `src/domain/users/interfaces.py`
- Implementation: `SqlAlchemyUserRepository` at `src/infrastructure/repositories/sqlalchemy_user_repository.py`
- Pattern: Domain interface defines contract, infrastructure implements with SQLAlchemy

**IAgentService (Interface):**
- Purpose: Abstract LLM-based conversation service
- Examples: `src/application/services/agent_service.py`
- Implementation: `LangChainAgentService` at `src/infrastructure/services/langchain_agent_service.py`
- Real service uses LangChain with GPT-4 or Anthropic Claude

**Use Cases:**
- Purpose: Orchestrate application logic and business rules
- Examples:
  - `AgentChatUseCase` at `src/application/chat/use_cases/agent_chat_use_case.py` (complex: ~200 lines)
  - `GetMonthlyUsageUseCase` at `src/application/usage/use_cases/get_monthly_usage_use_case.py` (simple: 16 lines, good for unit testing)
- Pattern: Single public `execute()` method that returns domain objects or DTOs

**Domain Events:**
- Purpose: Record fact that something happened (User created, Profile updated)
- Examples: `UserCreatedEvent`, `UserProfileUpdatedEvent` in `src/domain/events/domain_events.py`
- Collected in entities (e.g., `User._domain_events` list)
- Published to Redis event bus after persistence

---

## Entry Points

**Application Startup:**
- Location: `main.py` (project root)
- Triggers: `python -m uvicorn main:app --reload` or `docker-compose up`
- Responsibilities:
  - Creates FastAPI app via `create_application()`
  - Initializes `ApplicationContainer` during lifespan startup
  - Wires all routers with `/v1/api` prefix
  - Configures CORS, middleware, exception handlers
  - Returns app to uvicorn

**Health Endpoint:**
- Location: `src/presentation/api/routers/health.py`
- Triggers: `GET /health` (no auth required)
- Responsibilities:
  - Calls `container.health_check()` which checks database, LLM providers, event bus, agent service
  - Returns component status and entity counts

**Chat Endpoint (Primary):**
- Location: `src/presentation/api/routers/chat.py` lines 44-120
- Triggers: `POST /v1/api/chat` with JWT auth
- Responsibilities:
  - Validates message length (max 700 chars)
  - Calls `AgentChatUseCase.execute()`
  - Converts domain response to API response schema
  - Handles error cases with HTTPException

**Auth Endpoints:**
- Location: `src/presentation/api/routers/auth.py`
- Triggers: `POST /v1/api/auth/login`, `POST /v1/api/auth/register`
- Responsibilities: JWT token generation, user registration/login

**WebSocket Endpoint:**
- Location: `src/presentation/api/routers/ws.py`
- Triggers: `ws://localhost:8000/ws/{user_id}`
- Responsibilities: Real-time calendar updates via token-based authentication

---

## Error Handling

**Strategy:** Exception handling at multiple layers:
1. **Domain**: No exceptions (domain entities fail fast via invalid state)
2. **Application**: Raise `ApplicationException` from use cases with message + details
3. **Infrastructure**: Catch DB/service errors, wrap in `ApplicationException`
4. **Presentation**:
   - FastAPI validation errors → 422 Unprocessable Entity
   - ApplicationException → 400 Bad Request
   - Unhandled exceptions → 500 Internal Server Error
   - All errors logged to stdout and optionally CloudWatch

**Patterns:**

```python
# In use case (application layer)
if not user:
    raise ApplicationException("User not found", {"user_id": str(user_id)})

# In middleware (presentation layer)
try:
    response = await call_next(request)
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "internal_server_error"})

# In route handler
@app.exception_handler(ApplicationException)
async def app_exception_handler(request, exc: ApplicationException):
    return JSONResponse(status_code=400, content={"error": exc.message})
```

---

## Cross-Cutting Concerns

**Logging:**
- Framework: Python `logging` module
- Configuration: `settings.log_level` controls verbosity (DEBUG/INFO/WARNING/ERROR)
- Pattern: Each module has module-level logger: `logger = logging.getLogger(__name__)`
- CloudWatch: Optional integration via `CloudWatchLogger` in `src/infrastructure/observability/cloudwatch_logger.py` (enables optional mobile error logging)

**Validation:**
- Request DTOs: Pydantic models (`ChatApiRequest`, etc.) validate at FastAPI router entry
- Domain validation: Business rules in entity methods (e.g., `User.is_profile_complete()`)
- Custom validators: `src/presentation/api/validators/data_validators.py` for complex field validation

**Authentication:**
- Method: JWT Bearer tokens (HS256 symmetric)
- Implementation: `get_current_user_id()` in `src/presentation/dependencies.py` decodes JWT
- Token claims: `sub` (user UUID), `typ` ("access"), `iss` ("emotionai-api")
- Applied to: All `/v1/api/` routes except `/auth` (via FastAPI dependency)
- Known Issue: Hardcoded UUID fallback in `deps.py` (security bypass noted in CLAUDE.md)

**Rate Limiting:**
- Middleware: `RateLimitingMiddleware` at `src/presentation/api/middleware/rate_limiting.py`
- Configuration: `settings.rate_limit_requests` (requests per minute)
- Disabled in development if set to 0

**DI Wiring:**
- Container: `ApplicationContainer` at `src/infrastructure/container.py` lines 56-203
- Pattern: Factory method creates all instances in dependency order
- Real vs Stub Services:
  - **Real**: `LangChainAgentService` (uses GPT-4), `OpenAITaggingService` (uses GPT-4o-mini), `SqlAlchemyUserRepository`
  - **Stub**: `MockUserKnowledgeService` (returns empty/default), `MockSimilaritySearchService` (returns empty)
  - TODO comment at line 155: "Initialize mock services (to be replaced with full implementations)"

---

## Service Registry (Real vs Stub)

**Real Implementations (Production-Ready):**
- `LangChainAgentService` at `src/infrastructure/services/langchain_agent_service.py`: Full LangChain agent with memory, tools, GPT-4
- `OpenAITaggingService` at `src/infrastructure/services/openai_tagging_service.py`: Semantic tagging pipeline with GPT-4o-mini
- `SqlAlchemyUserRepository` and all other repos: Full SQLAlchemy CRUD with async/await
- `RedisEventBus` at `src/infrastructure/services/redis_event_bus.py`: Pub/sub messaging
- `ProfileService` at `src/infrastructure/services/profile_service.py`: User profile computation

**Stub Implementations (Placeholders):**
- `MockUserKnowledgeService` at `src/infrastructure/services/mock_user_knowledge_service.py`: Returns empty/default values, all methods no-op
- `MockSimilaritySearchService` at `src/infrastructure/services/mock_similarity_search_service.py`: Returns empty list, no-op

**Initialization Location:** `src/infrastructure/container.py` lines 118-177 create and register all services to container

---

*Architecture analysis: 2026-03-19*
