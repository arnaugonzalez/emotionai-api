# Codebase Concerns — EmotionAI API

**Analysis Date:** 2026-03-19

---

## Tech Debt Overview

The EmotionAI API has **36 documented technical debt items** across 4 severity levels: P0 (security/correctness blockers), P1 (architecture/reliability), P2 (performance/missing features), P3 (hygiene/polish).

Total: **8 P0**, **13 P1**, **11 P2**, **4 P3**

---

## P0 — Security & Correctness Blockers

These block release and expose the system to financial risk, data breaches, or complete authentication bypass.

### Authentication & Secrets

**TD-002 · No Password Hashing**
- Issue: All users created with plaintext `hashed_password="dev"` stub. Registration endpoint doesn't accept password. Login endpoint only checks email existence — no password verification.
- Files: `src/presentation/api/routers/auth.py` L60, `routers/records.py` L236, `routers/health.py` L41, `routers/dev_seed.py` L94
- Impact: Any user can log in as any other user by knowing their email. Zero authentication security. Production risk: complete user impersonation.
- Fix approach: Accept `password` field in registration, hash with `passlib[bcrypt]` (already in requirements), verify password hash on login, enforce during onboarding.

**TD-003 · Authentication Bypass — Fallback to Hardcoded UUID**
- Issue: `get_current_user_id` uses three-tier fallback: (1) `X-User-Id` header (spoofable), (2) Bearer token parsed as raw UUID without JWT validation, (3) hardcoded fallback UUID `550e8400-e29b-41d4-a716-446655440000`.
- Files: `src/presentation/api/routers/deps.py` L30–50
- Impact: Complete IDOR vulnerability. Any request without auth accesses placeholder user's data. `X-User-Id` header allows any client to impersonate any user. All user data leaks.
- Fix approach: Validate JWT from `Authorization` header using proper JWT library. Remove X-User-Id bypass and hardcoded fallback. Return 401 on invalid/missing tokens. Use `_parse_jwt` from `dependencies.py` everywhere.

**TD-004 · Hardcoded Default Secret Key**
- Issue: JWT signing key has default `"your-secret-key-here-change-in-production"` in `src/infrastructure/config/settings.py` L54. Validation only runs in production and logs warning instead of refusing startup.
- Files: `src/infrastructure/config/settings.py` L54
- Impact: In dev/staging, tokens signed with default key allow JWT forgery. Attackers can forge tokens if they know the default key (widely visible in code).
- Fix approach: Remove default value. Make `SECRET_KEY` required in all environments. Fail immediately at startup (before app init) if missing.

**TD-005 · Duplicate `get_current_user_id` with Different Behavior**
- Issue: Two independent implementations. `src/presentation/api/routers/deps.py` used by most routers. `src/presentation/dependencies.py` used by profile router — **always returns mock UUID regardless of token**.
- Files: `src/presentation/api/routers/deps.py` L24–50 vs `src/presentation/dependencies.py` L29–47
- Impact: Profile endpoints always operate on single hardcoded user. Profile get/put requests ignore the actual logged-in user.
- Fix approach: Consolidate to single `get_current_user_id` with proper JWT validation. Delete the unused implementation. Update profile router to use shared dependency.

### Data Integrity & Async

**TD-006 · All Core Repositories Are Empty Stubs**
- Issue: All repositories registered in DI container but return `None`/`[]`/`True` with `# TODO` placeholders. Routers bypass them with direct `session.execute(select(Model)...)` queries.
- Files:
  - `src/infrastructure/repositories/sqlalchemy_user_repository.py` (all methods stub)
  - `src/infrastructure/records/repositories/sqlalchemy_emotional_repository.py` (get_by_id returns None)
  - `src/infrastructure/breathing/repositories/sqlalchemy_breathing_repository.py`
  - `src/infrastructure/events/repositories/sqlalchemy_event_repository.py`
  - `src/infrastructure/analytics/repositories/sqlalchemy_analytics_repository.py`
- Impact: Clean architecture is facade. AI agent has no user context for personalization. Business logic cannot enforce invariants. Schema changes require edits in every router.
- Fix approach: Implement actual SQLAlchemy queries in each repository. Refactor routers to call use cases instead of directly accessing DB. Add proper error handling and transaction semantics.

**TD-007 · Blocking Sync Call in Async Context**
- Issue: `_check_duplicate_record` in `records.py` uses `session.execute(query)` (sync) instead of `await session.execute(query)`. Blocks event loop during duplicate check + Levenshtein distance calculation.
- Files: `src/presentation/api/routers/records.py` L64–90
- Impact: Under concurrent load, blocks all other requests while check runs. Single slow request stalls entire API.
- Fix approach: Change to `await session.execute(query)`, make function `async def`, profile Levenshtein performance or cache common strings.

**TD-008 · OpenAI Tagging Service Uses Sync Client in Async App**
- Issue: Uses `openai.OpenAI()` (synchronous) instead of `openai.AsyncOpenAI()`. All calls to `self.client.chat.completions.create()` block async event loop. Called on every tagged interaction.
- Files: `src/infrastructure/services/openai_tagging_service.py` L33
- Impact: Every tagging call (1–5 seconds) blocks all other async operations. Response latency spikes. Scale breaks at low concurrency.
- Fix approach: Switch to `openai.AsyncOpenAI`. Change `create()` calls to `await create()`. Validate that `openai_llm_service.py` already uses AsyncOpenAI correctly (it does).

---

## P1 — Architecture & Reliability

These damage code maintainability, introduce fragile abstractions, or cause data loss in edge cases.

### Architecture Violations

**TD-009 · Routers Directly Access Database Models**
- Issue: Every router imports SQLAlchemy models and performs direct `session.execute(select(Model)...)` queries. This is presentation → infrastructure dependency, violating clean architecture. Application/use-case layer completely bypassed.
- Files: All routers in `src/presentation/api/routers/`
- Impact: No business logic enforcement. No domain events fired. Schema changes require edits in every router. Impossible to audit data access.
- Fix approach: Route all data access through use cases that delegate to repositories. Routers should only call use cases and map response DTOs. Implement missing use cases.

**TD-018 · Inconsistent Router Prefix Strategy**
- Issue: Routes mounted with mixed prefixes: `health_router` → `/health`, `chat_router` → `/api/v1`, `records_router` → no prefix, `breathing_router` → no prefix. Flutter client expects `/v1/api/...` per contract.
- Files: `main.py` L128–140
- Impact: Mobile app routes break if endpoints shift. No consistent API versioning strategy.
- Fix approach: Mount all routers under consistent `/v1/api` prefix. Use middleware for `v1` versioning. Validate against actual Flutter client expectations.

### Duplicate Code & Dead Abstractions

**TD-010 · Duplicate Tagging Service Implementation**
- Issue: Two near-identical implementations. Container imports from `src/infrastructure/tagging/services/openai_tagging_service.py`. Root-level `src/infrastructure/services/openai_tagging_service.py` still exists (418 lines vs 358 lines).
- Files:
  - `src/infrastructure/services/openai_tagging_service.py` (418 lines, unused)
  - `src/infrastructure/tagging/services/openai_tagging_service.py` (canonical, 358 lines)
- Impact: Changes to one won't propagate to the other. They silently diverge. Hard to track which is active.
- Fix approach: Delete root-level file. Verify all imports point to nested location. Run grep for remaining references.

**TD-011 · Duplicate Data Validators**
- Issue: Same validation function names in two modules with different implementations.
- Files:
  - `src/data_validators.py` (84 lines, simpler)
  - `src/presentation/api/validators/data_validators.py` (198 lines, comprehensive)
- Impact: Unclear which validator is used. Root-level one appears unused but adds confusion.
- Fix approach: Delete `src/data_validators.py`. Verify imports in all routers use the full implementation.

**TD-012 · Duplicate Use Case Classes with Incompatible APIs**
- Issue: Two `AgentChatUseCase` files with **different signatures**:
  - `src/application/use_cases/agent_chat_use_case.py` uses `@dataclass`, takes `ChatRequest`
  - `src/application/chat/use_cases/agent_chat_use_case.py` uses plain `__init__`, takes individual params
- Files:
  - `src/application/use_cases/agent_chat_use_case.py` (dead, full tagging+knowledge pipeline)
  - `src/application/chat/use_cases/agent_chat_use_case.py` (canonical, container imports this)
- Impact: Root-level has intelligent tagging logic but is never called. Nested one is used but doesn't have same capabilities.
- Fix approach: Merge tagging logic from root-level into nested one. Delete root-level file. Update container if needed.

**TD-013 · Duplicate Tagging Service Interface**
- Issue: Same `ITaggingService` interface defined in two locations with potential divergence.
- Files:
  - `src/application/services/tagging_service.py`
  - `src/application/tagging/services/tagging_service.py`
- Impact: Implementations may reference different contracts. Refactoring becomes fragile.
- Fix approach: Keep nested location `src/application/tagging/services/`. Delete root-level. Update all imports.

**TD-014 · Shadowed `get_container` Redefinitions**
- Issue: Multiple routers import `get_container` from `deps` then redefine it locally, shadowing the import.
- Files: `src/presentation/api/routers/chat.py` L29–32, `src/presentation/api/routers/health.py` L20–22
- Impact: Unnecessary redefinition increases confusion. Inconsistent pattern across codebase.
- Fix approach: Remove local redefinitions. Use shared import from `deps.py`.

### Broken Abstractions & Mocks

**TD-015 · Redis Event Bus Is a Complete No-Op**
- Issue: Every method is `pass`. `health_check()` always returns `True` even if Redis is unreachable.
- Files: `src/infrastructure/services/redis_event_bus.py`
- Impact: Domain events silently dropped. Health check falsely reports Redis OK. Event-driven features don't work.
- Fix approach: Implement actual Redis pub/sub. Measure publish latency. At minimum, make health_check ping Redis and check response.

**TD-016 · Conversation History Returns Hardcoded Data**
- Issue: `GET /conversations` endpoint always returns same static placeholder regardless of user.
- Files: `src/presentation/api/routers/chat.py` L237–256
- Impact: Conversation history feature is broken. Clients show fake data to users.
- Fix approach: Query actual ConversationModel from database using user_id. Filter by user ownership.

**TD-017 · `LLMProviderFactory` Is a Mock**
- Issue: Always returns `MockLLMProvider` with hardcoded responses. Health check falsely reports `["openai", "anthropic"]` available.
- Files: `src/infrastructure/external/llm_providers.py`
- Impact: Health endpoint lies about LLM availability. Cannot switch providers.
- Fix approach: Implement properly or remove factory. Use `OpenAILLMService.health_check()` directly.

### Data Flow & Token Tracking

**TD-019 · Token Usage Not Tracked for Main Chat Responses**
- Issue: LLM service generates GPT-4 responses but never logs token consumption. Only tagging service tracks tokens.
- Files: `src/infrastructure/services/openai_llm_service.py`
- Impact: Usage endpoint reports inaccurate counts. Users hit limits unpredictably. No cost visibility.
- Fix approach: Inject `ITokenUsageRepository` into `OpenAILLMService`. Log tokens after each API call using response metadata (`usage.prompt_tokens`, `usage.completion_tokens`).

**TD-020 · Health Check Creates Database Records**
- Issue: `GET /health` creates placeholder user in non-production environments on every request.
- Files: `src/presentation/api/routers/health.py` L30–47
- Impact: Health checks should be read-only. Pollutes database with garbage users.
- Fix approach: Move user creation to startup lifecycle or dev seed endpoint. Health check should only query, never write.

### Deprecated Patterns

**TD-021 · Deprecated `datetime.utcnow()` Used Everywhere**
- Issue: `datetime.utcnow()` is deprecated since Python 3.12. Returns naive datetime without timezone info.
- Files: 20+ occurrences in `domain/entities/user.py`, `domain/events/domain_events.py`, `infrastructure/services/`, `application/dtos/chat_dtos.py`
- Impact: Naive datetimes lose timezone context. Comparisons may fail across DST boundaries. Deprecation warning in Python 3.12+.
- Fix approach: Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)` throughout. Test datetime edge cases.

---

## P2 — Performance & Missing Functionality

These cause slowdowns, missing features, or dead dependencies that inflate supply chain risk.

### Missing Endpoints & Features

**TD-022 · Missing Pagination on All List Endpoints**
- Issue: All list endpoints return **all records** for a user with no `limit`/`offset` parameters.
- Files: `routers/records.py` L155, `routers/breathing.py` L41, `routers/data.py` L41
- Impact: Response time degrades as data grows. Unbounded payloads. Violates REST best practices.
- Fix approach: Add `limit: int = 50` and `offset: int = 0` query parameters. Apply `.limit().offset()` in SQLAlchemy queries. Document defaults in OpenAPI.

**TD-023 · No DELETE Endpoints for Any Resource**
- Issue: No CRUD resources have `DELETE` endpoints. Flutter app cannot delete data from server.
- Files: All routers
- Impact: Users cannot correct mistakes or remove old data. Data accumulation. Privacy concern.
- Fix approach: Add `DELETE /{resource}/{id}` endpoints for emotional_records, breathing_sessions, custom_emotions. Validate ownership. Soft-delete or hard-delete per policy.

**TD-024 · No UPDATE Endpoints for Records/Sessions**
- Issue: No `PUT`/`PATCH` endpoints. Once created, data cannot be corrected.
- Files: `routers/records.py`, `routers/breathing.py`
- Impact: Users locked into incorrect data. No data correction flow.
- Fix approach: Add `PUT /{resource}/{id}` with full replacement or `PATCH` with partial updates. Validate ownership. Update timestamp.

**TD-025 · Hardcoded Monthly Token Limit**
- Issue: 250K limit hardcoded in router. Cannot be changed per-user, per-plan, or via configuration.
- Files: `src/presentation/api/routers/usage.py` L30
- Impact: Cannot implement tiered pricing. All users same limit. No way to test quota enforcement.
- Fix approach: Move to `settings.py` with env var override. Add per-user limit column in database. Check during chat to enforce.

### Performance & Scaling

**TD-026 · In-Memory Rate Limiting Won't Scale**
- Issue: Uses in-memory `defaultdict(list)`. With `workers: 4`, each worker maintains independent counters. Dictionary grows unboundedly.
- Files: `src/presentation/api/middleware/rate_limiting.py`
- Impact: With 4 workers, limit is 4× higher than configured (400 requests instead of 100). Unbounded dict memory leak.
- Fix approach: Use Redis-backed sliding window rate limiting. Use `INCR` with `EXPIRE` pattern. Share counters across workers.

### Database & Repository Issues

**TD-027 · Conversation Repository Bypasses Session Context Manager**
- Issue: Uses `async_session_factory()` directly instead of `self.database.get_session()`, bypassing automatic commit/rollback/cleanup.
- Files: `src/infrastructure/conversations/repositories/sqlalchemy_conversation_repository.py` L48
- Impact: Transactions may not commit/rollback properly. Resources may leak.
- Fix approach: Use `async with self.database.get_session() as session:` consistently. Review all repositories.

**TD-028 · Conversation Repository Stores UUIDs as Strings**
- Issue: Model defines `Column(UUID(as_uuid=True))` but repository passes `str(uuid4())`.
- Files: `src/infrastructure/conversations/repositories/sqlalchemy_conversation_repository.py` L39–42
- Impact: Type inconsistency. Query filters may fail. Serialization issues.
- Fix approach: Pass raw `uuid4()` objects. Let SQLAlchemy handle conversion.

**TD-029 · `DatabaseConnection._get_connect_args` Returns Invalid Keys**
- Issue: `poolclass=StaticPool` placed inside `connect_args` — it's an engine-level parameter, not driver-level.
- Files: `src/infrastructure/database/connection.py` L105–112
- Impact: Invalid for `psycopg2`/`asyncpg`. May cause initialization errors.
- Fix approach: Move `poolclass=StaticPool` to `create_engine()` call. Keep driver args only in `connect_args`.

**TD-030 · `ApplicationContainer._get_uptime()` Broken Pattern**
- Issue: `ApplicationContainer` is `@dataclass`. Setting `self._start_time` in method initializes on first call, not at creation.
- Files: `src/infrastructure/container.py` L291–298
- Impact: Uptime calculation inaccurate. First request triggers initialization.
- Fix approach: Add `_start_time: float = field(default_factory=time.time, init=False)` as dataclass field.

### Dead Dependencies

**TD-031 · Dead Dependencies in `requirements.txt`**

| Package | Status |
|---------|--------|
| `dependency-injector>=4.41.0` | Never imported (container is handwritten) |
| `chromadb>=0.4.0` | Configured in settings but never wired in container |
| `qdrant-client>=1.7.0` | Configured but never wired |
| `aiocache>=0.12.0` | Never imported |
| `langchain>=0.0.300` | Never imported (openai used directly) |
| `psycopg2-binary>=2.9.0` | Barely used (async app uses asyncpg) |

Impact: Inflates dependencies, increases install time, expands supply chain surface, adds security scanning load.

Fix approach: Remove each dead dependency. Verify no imports or references exist. Test after removal.

**TD-032 · Dead Dependencies in `requirements-production.txt`**

| Package | Status |
|---------|--------|
| `anthropic==0.7.6` | Never imported |
| `aiohttp==3.9.1` | Never imported (httpx used) |
| `uuid==1.30` | Python has built-in `uuid` module |
| `sentry-sdk[fastapi]==1.38.0` | Never configured or imported |
| `gunicorn==21.2.0` | Listed **twice** (lines 3 and 41) |
| `structlog==23.2.0` | Never imported (stdlib logging used) |
| `langchain==0.0.335`, `langchain-openai==0.0.2` | Never imported |

Impact: Bloats production image. Unused versions may have security issues. Duplicate gunicorn entry causes confusion.

Fix approach: Remove each unused package. Keep gunicorn once. Test cold start time after cleanup.

---

## P3 — Hygiene & Polish

These reduce code quality, increase cognitive load, or hide issues.

### Dead Code & Structure

**TD-033 · `legacy_backup/` Directory Is Dead Code**
- Path: `legacy_backup/`
- Contents: `agents/`, `api/`, `services/`, `app/`, `core/`, `models/`
- Impact: Confuses developers. May be referenced incorrectly. Clutters codebase.
- Fix approach: Verify nothing in src/ imports from it (use grep). Delete entire directory.

**TD-034 · Empty `src/presentation/api/main.py`**
- Issue: File exists but is whitespace-only. CLAUDE.md claims it's the "app factory" — but there is no factory.
- Files: `src/presentation/api/main.py`
- Impact: Misleading documentation. Unclear purpose.
- Fix approach: Implement app factory (move `create_app` logic here) or delete and update docs.

**TD-035 · `src/domain/repositories/` Contains No Code**
- Issue: Empty `__init__.py` only. All actual repository interfaces live in feature-scoped directories.
- Impact: Unused directory. Violates clean architecture structure expectations.
- Fix approach: Delete or use as aggregate re-export of all repository interfaces.

**TD-036 · `presentation/dependencies.py` Is Mostly Dead Code**
- Issue: Defines 7 provider functions but only `get_current_user_id` and `get_profile_service` imported (by profile.py). The `get_current_user_id` here is broken (always mock UUID).
- Files: `src/presentation/dependencies.py`
- Impact: Confusion about which auth function to use. Dead code suggests unclear design.
- Fix approach: Delete unused functions. Consolidate with `deps.py`. One auth dependency.

### Type & Validation Issues

**TD-037 · Untyped Request Bodies**
- Issue: Raw `dict` instead of Pydantic models in several routers.
- Files: `auth.py` (`payload: dict`), `records.py` (`record: Dict[str, Any]`), `breathing.py` (`session_body: Dict`), `data.py` (`payload: Dict`)
- Impact: No automatic validation. No OpenAPI schema for request bodies. Harder to debug client errors.
- Fix approach: Define Pydantic request models for all endpoints. Inherit from DTO models in `src/application/dtos/`.

**TD-038 · Inconsistent Error Response Format**
- Issue: Error responses vary between endpoints: `{"detail": "..."}`, `{"error": "...", "message": "..."}`, `{"status": "unhealthy", "error": "..."}`, `{"detail": {"message": ..., "code": ..., "suggestion": ...}}`.
- Files: Multiple routers
- Impact: Clients cannot parse errors uniformly. Inconsistent API contract.
- Fix approach: Standardize to `{"error": "code", "message": "human-readable", "details": {}}` everywhere. Add global error formatter in middleware.

### Security & Logging

**TD-039 · No Token Invalidation / Logout Is a No-Op**
- Issue: Logout endpoint is `# TODO: Implement token invalidation` + returns success message without doing anything.
- Files: `src/presentation/api/routers/auth.py` L113
- Impact: Tokens valid forever. User cannot actually log out. Sessions impossible to revoke.
- Fix approach: Implement Redis-backed token blacklist. Check blacklist before each request. Set TTL to match token expiry.

**TD-040 · `CORS_ORIGINS=["*"]` in All Environments**
- Issue: CORS allows all origins. Production should be restrictive.
- Files: `settings.py` L78, `docker-compose.yml` L44
- Impact: Any website can make requests to API. Credentials leakage. Not production-safe.
- Fix approach: Set explicit origins for production (only emotionai-app domain). Keep `["*"]` for dev. Make configurable via env.

**TD-041 · `uvicorn.run()` Binds to `0.0.0.0`**
- Issue: Documentation says "bound to `127.0.0.1`" but code binds to `0.0.0.0`, exposing API on all interfaces.
- Files: `main.py` L203
- Impact: API reachable from outside container. Unintended exposure in dev. Should be proxied by Nginx in production.
- Fix approach: Bind to `127.0.0.1` in production. Make `host` configurable via settings. Validate in tests.

**TD-043 · Verbose Debug Logging of Response Content**
- Issue: Full therapy response objects logged at `INFO` level, exposing sensitive patient data.
- Files: `src/presentation/api/routers/chat.py` L78–87
- Impact: Mental health data in logs. HIPAA/privacy violation if logs are breached. Retention issue.
- Fix approach: Move to `DEBUG` level only. Redact sensitive fields (emotion, content, crisis_detected). Log only metadata.

**TD-044 · Error Messages Leak Internal State**
- Issue: Exception details returned to client: `{"exception_type": type(e).__name__, "exception_message": str(e)}`.
- Files: `src/presentation/api/routers/chat.py` L135–139
- Impact: Stack traces visible to attacker. Internal implementation leaked. Aids reconnaissance.
- Fix approach: Log full details server-side. Return generic error code to client. Use error code lookup instead of raw exception.

### Environment & Compatibility

**TD-042 · PostgreSQL 13 in Docker vs 16 in Production**
- Issue: Dev runs `postgres:13`, production runs PostgreSQL 16 (AWS RDS).
- Files: `docker-compose.yml` (`postgres:13`), `aws_infra_terraformer/rds.tf` (PostgreSQL 16)
- Impact: Feature compatibility may differ. SQL dialect changes. Development surprises in production.
- Fix approach: Upgrade docker-compose to `postgres:16` to match production.

### Unused Code

**TD-045 · Unused Imports and Dead Code**
- Issue: Scattered across files.
- Files: `records.py` (`import hashlib`), `main.py` (`import asyncio`), `chat.py` (`HTTPBearer` defined but unused)
- Impact: Clutter. Confuses code readers. May mask actual unused functionality.
- Fix approach: Automated linting with `ruff` or `flake8`. Remove unused imports. Use in pre-commit hook.

### Mock Services

**TD-046 · Mock Services Are Stubs with No Logic**
- Issue: `ISimilaritySearchService` and `IUserKnowledgeService` always return empty/dummy results. Vector DB configured in settings but never wired.
- Files:
  - `src/infrastructure/services/mock_similarity_search_service.py`
  - `src/infrastructure/services/mock_user_knowledge_service.py`
- Impact: Agent cannot perform semantic memory retrieval. Personalization broken.
- Fix approach: Implement ChromaDB or Qdrant integration. Wire in `container.py`. Test memory retrieval end-to-end.

### Alembic & Migrations

**TD-047 · Single Monolithic Alembic Migration**
- Issue: All schema changes in `migrations/versions/001_initial_schema.py`. Editing it breaks any DB that has applied it.
- Files: `migrations/versions/001_initial_schema.py`
- Impact: Impossible to fix past migrations. Cannot roll back changes safely. Blocks team from iterating on schema.
- Fix approach: **Never touch `001_`**. Every future schema change: `alembic revision --autogenerate -m "describe_change"`. Document this rule.

### Additional Observations

**TD-048 · No Request Size Limits**
- Issue: No middleware limits request body size.
- Impact: Malicious clients can send arbitrarily large payloads (megabytes). DoS vector. Memory exhaustion.
- Fix approach: Add body size limit middleware. Set reasonable max (e.g., 10MB). Enforce via Nginx config as well.

**TD-049 · Missing `__all__` Exports in `__init__.py`**
- Issue: Most `__init__.py` files are empty.
- Impact: IDE auto-import doesn't work well. `from package import *` doesn't work. Unclear public API.
- Fix approach: Add `__all__` lists to key `__init__.py` files, especially in domain and application layers.

---

## Cross-Cutting Issues (Shared with App)

**XC-001 · Sync DELETE not implemented** — App deletes reappear after sync. API has no DELETE endpoints (TD-023).

**XC-002 · No JWT token refresh** — Silent 401s after 30-minute token expiry. No refresh token flow.

**XC-003 · API contract not typed** — No OpenAPI client generation. Dart client manually maintained, prone to drift.

**XC-004 · Physical device IP hardcoded** — Flutter app has hardcoded IP in `lib/config/api_config.dart`.

---

## Attack Priority

### Sprint 1 — Security (P0) — Estimated 3 sprints
1. **TD-002**: Implement password hashing in auth flow
2. **TD-003**: Replace auth bypass with proper JWT validation
3. **TD-004**: Make SECRET_KEY required in all environments
4. **TD-005**: Consolidate `get_current_user_id` implementations
5. **TD-007**: Fix blocking sync call in duplicate check
6. **TD-008**: Switch OpenAI tagging to AsyncOpenAI

### Sprint 2 — Correctness (P0/P1) — Estimated 2 sprints
1. **TD-006**: Implement repository methods and refactor routers to use use cases
2. **TD-020**: Move health check user creation to startup
3. **TD-021**: Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`

### Sprint 3 — Architecture (P1) — Estimated 2 sprints
1. **TD-009**: Refactor routers to use use cases instead of direct DB access
2. **TD-010, TD-011, TD-012, TD-013**: Consolidate duplicate code
3. **TD-014**: Remove shadowed `get_container` definitions
4. **TD-015, TD-016, TD-017**: Implement broken abstractions (event bus, conversation history, LLM factory)
5. **TD-018**: Fix router prefix strategy

### Sprint 4 — Features (P2) — Estimated 2 sprints
1. **TD-022**: Add pagination to list endpoints
2. **TD-023, TD-024**: Add DELETE and UPDATE endpoints
3. **TD-019**: Track token usage in main LLM service
4. **TD-025**: Make token limit configurable

### Sprint 5 — Scale & Performance (P2) — Estimated 1 sprint
1. **TD-026**: Switch rate limiting to Redis
2. **TD-031, TD-032**: Remove dead dependencies
3. **TD-027, TD-028, TD-029, TD-030**: Fix database quirks

### Sprint 6 — Polish (P3) — Estimated 1 sprint
1. **TD-033, TD-034, TD-035, TD-036**: Clean up dead code
2. **TD-037, TD-038**: Add Pydantic models, standardize error responses
3. **TD-039, TD-040, TD-041**: Fix logout, CORS, host binding
4. **TD-042**: Upgrade docker-compose Postgres to 16
5. **TD-043, TD-044**: Fix logging & error messages
6. **TD-045**: Remove unused imports
7. **TD-046**: Implement vector DB integration
8. **TD-047**: Document Alembic migration policy
9. **TD-048, TD-049**: Add request size limits, `__all__` exports

---

*Concerns audit: 2026-03-19*
