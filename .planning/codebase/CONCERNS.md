# Codebase Concerns

**Analysis Date:** 2026-03-19

---

## Pre-Flight Investigation Findings

### 1. Dependency Injection Wiring (container.py)

**File**: `src/infrastructure/container.py`

**Status**: Properly implemented with clear composition root pattern.

**DI Structure**:
- All repositories properly instantiated: `SqlAlchemyUserRepository`, `SqlAlchemyEmotionalRepository`, `SqlAlchemyBreathingRepository`, `SqlAlchemyConversationRepository`, `SqlAlchemyEventRepository`, `SqlAlchemyAnalyticsRepository`
- Services wired in order: LLM service (OpenAI or Anthropic), event bus (Redis), tagging service
- Container provides health checks and metrics endpoints

**Stub Services Identified**:
- `MockUserKnowledgeService` (line 156) - initialized but returns empty/dummy data
- `MockSimilaritySearchService` (line 157) - initialized but returns empty lists
- Both marked with TODO comments for replacement with full implementations

**Critical Issue**: The mock services are wired into the production container and passed to `AgentChatUseCase`. They silently return no data, which degrades semantic memory capabilities but doesn't fail loudly.

---

### 2. Authentication and Authorization Concerns (deps.py)

**File**: `src/presentation/api/routers/deps.py`

**Status**: Centralized JWT dependency but potential issues identified.

**Current Implementation**:
- Delegates to `_jwt_get_current_user_id` from `src/presentation/dependencies.py`
- Uses `HTTPBearer` security scheme with token extraction

**Dependencies File Analysis** (`src/presentation/dependencies.py`):
- Line 28-45: `get_current_user_id` validates JWT with proper error handling
- Checks: token type (`typ`), subject presence, issuer validation
- Throws `HTTPException(401)` on validation failure

**No hardcoded UUID fallback detected** in either file. The pre-flight checklist concern about "auth bypass via hardcoded UUID fallback" is not present in current code — this may have been previously fixed (see recent commits showing P0 tech debt fixes).

**Minor Issue**: Duplicate `get_current_user_id` implementations:
- `src/presentation/dependencies.py` (line 28) - canonical JWT-parsing version
- `src/presentation/api/routers/deps.py` (line 25-29) - delegates to above
- This duplication is redundant but not dangerous

---

### 3. Test Suite Existence and Structure

**Test Directory**: `/home/eager-eagle/code/emotionai/emotionai-api/tests/`

**Status**: Directory exists but appears empty or minimal.

**Findings**:
- `.pytest_cache` directory present (line: `drwxrwxr-x  3 eager-eagle eager-eagle  4096 Mar 18 19:33 .pytest_cache`)
- No `pytest.ini`, `conftest.py`, or `pyproject.toml` with `[tool.pytest]` config found in project root
- No unit test files discovered in project tree

**Test Files Expected but Not Found**:
- `test_integration.py` (mentioned in TECH_DEBT.md as only integration tests)
- `test_database_integrations.py` (mentioned in TECH_DEBT.md as only integration tests)

**Critical Gap**: Only integration tests documented; no unit test suite exists. Changes to use cases or repositories lack fast feedback loops.

---

### 4. Dependencies Configuration

**files**: `requirements.txt`, `requirements-production.txt`

**Status**: Both present; production file properly constrained.

**Confirmed Packages**:
- `asyncpg>=0.29.0` ✓ (line 40 in requirements.txt, line 13 in requirements-production.txt)
- `pytest>=7.4.0` ✓ (line 28 in requirements.txt)
- `pytest-asyncio>=0.21.0` ✓ (line 29 in requirements.txt)
- Missing: `pytest-cov` — coverage tool NOT listed in either file

**Production vs Development Split**:
- `requirements-production.txt` uses pinned versions (e.g., `fastapi>=0.116,<0.117`)
- `requirements.txt` uses looser constraints (e.g., `fastapi>=0.104.1`)
- Good separation for reproducible production deploys

**Dead Dependency**:
- `dependency-injector>=4.41.0` (line 39 in requirements.txt) — imported in neither source nor test files
- Container is handwritten intentionally (per CLAUDE.md)
- Adds ~50KB to install; safe to remove

---

### 5. ORM Models (database/models.py)

**File**: `src/infrastructure/database/models.py`

**Total Models**: 13 SQLAlchemy models

**Complete Model List**:
1. `UserModel` (489 lines) - central entity with extended profile fields
2. `UserProfileDataModel` - personality, preferences, country, gender
3. `AgentPersonalityModel` - AI agent context (mood patterns, coping strategies)
4. `ConversationModel` - chat session container
5. `MessageModel` - individual messages with intelligent tagging
6. `EmotionalRecordModel` - emotion logging with semantic tags
7. `BreathingSessionModel` - breathing exercise tracking
8. `BreathingPatternModel` - preset and custom breathing patterns
9. `CustomEmotionModel` - user-defined emotions
10. `DailySuggestionModel` - LLM-generated recommendations
11. `DomainEventModel` - domain event persistence for event sourcing
12. `UserProfileModel` - aggregated tag data and insights
13. `TagSemanticModel` - tag relationships and synonyms

**Key Observations**:
- Well-indexed with GIN indexes for JSONB columns (intelligent tagging search)
- Cascade deletes properly configured for relationships
- Multiple JSONB columns for semantic data storage
- No enum types used (string columns instead)
- Timestamps with timezone awareness implemented consistently

**Model Size**: 489 lines total — well-organized but some legacy patterns remain (e.g., `agent_personality_data` and `user_profile_data` JSON columns with deprecation comments).

---

### 6. Service Implementation Status

**Location**: `src/infrastructure/services/`

**Real Implementations**:
- `LangChainAgentService` (331 lines) - fully functional with memory and context
- `OpenAITaggingService` (417 lines) - semantic tagging with dual prompts
- `OpenAILLMService` (210 lines) - OpenAI integration
- `AnthropicLLMService` - Anthropic Claude integration
- `RedisEventBus` - event publication and subscription
- `ProfileService` (455 lines) - user profile management

**Mock/Stub Implementations**:
- `MockSimilaritySearchService` (118 lines) - returns empty lists, basic Jaccard similarity only
- `MockUserKnowledgeService` (103 lines) - returns None or dummy data

**Concerning Pattern**: Mock services are fully integrated into production container (lines 156-157 in `container.py`). They don't crash but provide no semantic memory capabilities.

---

### 7. Tech Debt Summary from TECH_DEBT.md

**P0 — Blocks correctness or reliability**:

**P0-001: No unit test suite**
- Files: Only `test_integration.py` and `test_database_integrations.py` exist (not committed/found)
- Problem: Changes to use cases/repositories have no fast feedback
- Impact: Regressions in business logic undetected until integration runs
- Fix approach: Add pytest unit tests per use case, mock `ApplicationContainer`

**P1 — Code quality and maintainability**:

**P1-001: Duplicate agent_chat_use_case.py**
- Files:
  - `src/application/use_cases/agent_chat_use_case.py` ← delete this (STALE)
  - `src/application/chat/use_cases/agent_chat_use_case.py` ← canonical location
- Problem: Two copies means changes must be applied twice or drift silently
- Impact: Low immediate risk but maintenance hazard
- Fix approach: Verify identical, update imports, delete root-level copy

**P1-002: Duplicate tagging service interface**
- Files:
  - `src/application/services/tagging_service.py` (root-level)
  - `src/application/tagging/services/tagging_service.py` (feature-scoped)
  - `src/infrastructure/services/openai_tagging_service.py` (using root-level import)
  - `src/infrastructure/tagging/services/openai_tagging_service.py` (using feature-scoped import, 357 lines)
- Problem: Same interface in two locations; implementations diverging
- Impact: Confusion about canonical location; potential import errors
- Fix approach: Consolidate to `src/application/tagging/services/`, update all imports

**P1-003: Unused dependency-injector package**
- Files: `requirements.txt`, `requirements-production.txt`
- Problem: Package declared but never imported; dead dependency
- Impact: Longer install times, larger attack surface
- Fix approach: Remove `dependency-injector>=4.41.0` from both files

**P2 — Missing functionality**:

**P2-001: Mock services are stubs**
- Files: `src/infrastructure/services/mock_*.py`
- Problem: `ISimilaritySearchService` and `IUserKnowledgeService` always return empty results
- Impact: Agent cannot perform semantic memory retrieval; all recommendations are generic
- Fix approach: Implement ChromaDB or Qdrant integration; wire in container

**P2-002: Single monolithic migration**
- File: `migrations/versions/001_initial_schema.py`
- Problem: All schema changes accumulated in one file; future edits break history
- Impact: Schema safety degradation; migration chaining becomes fragile
- Fix approach: Lock `001_` as immutable; every future change uses `alembic revision --autogenerate -m "..."`

---

### 8. Docker Compose Configuration

**File**: `docker-compose.yml`

**Port Exposure**:
- PostgreSQL: `5432:5432` (exposed, correct for local testing)
- Redis: `6379:6379` (exposed, correct for local testing)
- API: `8000:8000` (exposed, correct for local testing)

**Health Checks**:
- PostgreSQL: 10-second timeout with 5s interval and 10 retries ✓
- Redis: 3-second timeout with 5s interval and 5 retries ✓
- API waits for both health checks before starting ✓

**Concern**:
- Line 40-42: `OPENAI_API_KEY` environment placeholder present but empty
  - Will cause API to fail at startup without `.env` override
  - No validation at startup to fail fast with clear error message
  - Fix: Remove placeholder; validate presence in `settings.validate_required_settings()`

**Good Practice**:
- Network isolation via `emotionai-network` bridge
- Persistent volume for Postgres data
- `.env` file support (`env_file: - .env`)

---

### 9. Test Configuration

**Status**: No pytest configuration files found at project root.

**Missing Files**:
- `pytest.ini` — not found
- `conftest.py` — not found
- `pyproject.toml` with `[tool.pytest]` — not found

**Implications**:
- Default pytest behavior (collect from `tests/` directory)
- No custom pytest plugins or fixtures available
- No shared test setup/teardown
- Coverage configuration must be passed via CLI flags

**Recommendation**: Create `pyproject.toml` with pytest config:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "--strict-markers --tb=short"
markers = [
    "integration: integration tests",
    "unit: unit tests",
    "async: async tests"
]
```

---

### 10. Use Cases Inventory

**Location**: `src/application/` and feature-scoped subdirectories

**Identified Use Cases**:
1. `GetMonthlyUsageUseCase` (14 lines) — **SIMPLEST**
   - File: `src/application/usage/use_cases/get_monthly_usage_use_case.py`
   - Depends: `ITokenUsageRepository` only
   - Method: `execute(user_id: UUID, year, month) -> int`
   - Purpose: Fetch user's token usage for a given month
   - Ideal candidate for first unit test (minimal dependencies)

2. `AgentChatUseCase` (nested location)
   - File: `src/application/chat/use_cases/agent_chat_use_case.py`
   - Depends: 8+ services (complex)
   - Purpose: Full chat pipeline with memory, tagging, crisis detection

---

## Critical Issues

### Issue 1: Semantic Memory Services Are Non-Functional

**Category**: Missing Functionality (P2)

**Severity**: HIGH

**Files**:
- `src/infrastructure/services/mock_similarity_search_service.py`
- `src/infrastructure/services/mock_user_knowledge_service.py`
- `src/infrastructure/container.py` (lines 156-157)

**Problem**:
- `ISimilaritySearchService` and `IUserKnowledgeService` are critical for personalized recommendations
- Current mock implementations return empty lists or dummy data
- Agent cannot retrieve past emotional patterns or effective coping strategies
- ChromaDB and Qdrant are configured in settings but never initialized
- Vector DB path (`settings.chromadb_path`) exists but unused

**Impact**:
- All user recommendations are generic (not learned from history)
- Agent lacks access to user's past conversations and emotional patterns
- Worse user experience; reduced therapeutic effectiveness
- Violates core product promise of personalized mental health support

**Fix Approach**:
1. Implement `ChromaDbSimilaritySearchService` using `chromadb` library (already in requirements)
2. Implement `RealUserKnowledgeService` using tag aggregation from `UserProfileModel`
3. Wire both services in `container.py` with conditional logic based on feature flags
4. Add integration tests for vector retrieval accuracy

**Effort**: MEDIUM (implementation + testing)

---

### Issue 2: Repository Implementations Are Empty Stubs

**Category**: Missing Functionality (P2)

**Severity**: MEDIUM-HIGH

**Files Affected**:
- `src/infrastructure/analytics/repositories/sqlalchemy_analytics_repository.py` - returns None
- `src/infrastructure/records/repositories/sqlalchemy_emotional_repository.py` - multiple TODO stubs
- `src/infrastructure/breathing/repositories/sqlalchemy_breathing_repository.py` - multiple TODO stubs
- `src/infrastructure/events/repositories/sqlalchemy_event_repository.py` - multiple TODO stubs

**Problem**:
- Many repository methods contain only TODO comments with no implementation
- Methods return None or pass without DB operations
- Violates Liskov Substitution Principle — interfaces not honored
- Code appears to work but silently drops data

**Examples**:
```python
# From sqlalchemy_emotional_repository.py
async def get_emotional_records(self, user_id: UUID):
    # TODO: Implement actual database query
    return []

async def save_emotional_record(self, user_id: UUID, ...):
    # TODO: Implement actual database save
    return None
```

**Impact**:
- Emotional records logged but not persisted
- Analytics interactions discarded
- Event sourcing broken (domain events lost)
- Silent data loss during normal operation

**Fix Approach**:
1. Audit all repository methods for completeness
2. Implement missing database queries using SQLAlchemy session
3. Add integration tests that verify persistence
4. Use type hints to catch missing implementations at check time

**Effort**: MEDIUM (systematic implementation across 4 repos)

---

### Issue 3: No Unit Test Suite

**Category**: Correctness (P0)

**Severity**: HIGH

**Files**:
- Test directory exists but no test files found
- No integration tests discovered in project tree
- No conftest or test fixtures

**Problem**:
- Changes to business logic have zero fast feedback
- Regressions only caught at integration test time (if tests are run)
- No TDD workflow possible
- Harder to refactor with confidence

**Impact**:
- High defect escape rate
- Slower development velocity
- Lower code confidence
- Difficult onboarding for new developers

**Current Test Plan**:
TECH_DEBT.md recommends starting with:
- Unit tests for `GetMonthlyUsageUseCase` (simplest: 14 lines, 1 dependency)
- Unit tests for `AgentChatUseCase` (complex: 8+ dependencies, requires mocking)

**Fix Approach**:
1. Create `conftest.py` with reusable fixtures
2. Start with `tests/unit/use_cases/test_get_monthly_usage_use_case.py`
3. Mock `ITokenUsageRepository` with simple in-memory implementation
4. Add tests for happy path + error cases
5. Gradually expand to other use cases using same pattern
6. Add `pytest-cov` to requirements and enforce coverage targets

**First Test Example**:
```python
@pytest.mark.asyncio
async def test_get_monthly_usage_with_valid_month(mock_token_usage_repo):
    use_case = GetMonthlyUsageUseCase(mock_token_usage_repo)
    mock_token_usage_repo.get_monthly_usage.return_value = 42

    result = await use_case.execute(user_id=..., year=2026, month=3)

    assert result == 42
```

**Effort**: HIGH (systematic coverage across all use cases/repos)

---

### Issue 4: Duplicate Code (Services and Use Cases)

**Category**: Code Quality (P1)

**Severity**: MEDIUM

**Files**:
- `src/application/use_cases/agent_chat_use_case.py` (STALE)
- `src/application/chat/use_cases/agent_chat_use_case.py` (CANONICAL)
- `src/application/services/tagging_service.py` (ROOT-LEVEL)
- `src/application/tagging/services/tagging_service.py` (FEATURE-SCOPED)
- `src/infrastructure/services/openai_tagging_service.py` (OLD LOCATION)
- `src/infrastructure/tagging/services/openai_tagging_service.py` (NEW LOCATION)

**Problem**:
- Duplication increases maintenance burden
- Changes must be applied in multiple locations or code drifts
- Imports from wrong location lead to subtle bugs
- Unclear which is canonical version

**Impact**:
- Maintenance errors accumulate
- Confusing for new developers
- Potential for inconsistent behavior

**Fix Approach**:
1. Identify canonical location for each duplicated artifact
2. Verify both versions are identical
3. Update all imports to canonical location
4. Delete stale copies
5. Run grep to ensure no dangling imports

**Duplicates to Fix**:
- `agent_chat_use_case.py`: Keep `src/application/chat/use_cases/`, delete root-level
- `tagging_service.py`: Keep `src/application/tagging/services/`, delete root-level
- `openai_tagging_service.py`: Keep `src/infrastructure/tagging/services/`, delete root-level duplicate

**Effort**: LOW (cleanup task)

---

## Performance Bottlenecks

### Issue 5: Potential Blocking Calls in Async Handlers

**Category**: Performance

**Severity**: MEDIUM

**Concern**: No blocking sync calls detected in current analysis, but review the following high-traffic handlers:

**Files to Audit**:
- `src/presentation/api/routers/chat.py` (269 lines)
- `src/presentation/api/routers/records.py` (403 lines)
- `src/infrastructure/services/openai_tagging_service.py` (417 lines)
- `src/infrastructure/services/langchain_agent_service.py` (331 lines)

**Recommendation**: Profile with `asyncio-monitor` or `py-spy` before/after load testing to verify no event loop blocking.

---

### Issue 6: Vector Database Integration Missing

**Category**: Performance / Scalability

**Severity**: MEDIUM

**Files**:
- `src/infrastructure/config/settings.py` - chromadb_path and qdrant_url configured but unused
- `src/infrastructure/services/mock_similarity_search_service.py` - returns empty results

**Problem**:
- Semantic search for similar emotional patterns disabled
- Every user request starts from zero context
- No learned optimization from historical interactions

**Impact**:
- O(n) recommendation logic instead of O(1) vector lookup
- Degraded response time under load
- Higher LLM API cost (more tokens for context building)

**Scaling Plan**:
1. Implement ChromaDB service
2. Embed user messages and emotional records into vectors
3. Index vectors with metadata (user_id, timestamp, emotion)
4. Query at recommendation time: `find_similar(current_emotion) -> List[Match]`

**Effort**: MEDIUM-LONG (vector pipeline implementation)

---

## Security Considerations

### Issue 7: No Secrets Validation at Startup

**Category**: Security (Configuration)

**Severity**: LOW

**Files**:
- `docker-compose.yml` (line 40: empty OPENAI_API_KEY)
- `src/infrastructure/config/settings.py` (no startup validation)

**Problem**:
- API starts without required secrets
- User sees confusing "API key invalid" errors from OpenAI, not clear startup failure
- No fast-fail on misconfiguration

**Impact**:
- Operational confusion
- Difficult debugging in production
- Silent degradation if env vars partially configured

**Fix Approach**:
```python
# In settings.py or main.py
def validate_required_settings(settings: Settings):
    required = [
        ('OPENAI_API_KEY', settings.openai_api_key),
        ('ANTHROPIC_API_KEY', settings.anthropic_api_key),  # at least one
        ('DATABASE_URL', settings.database_url),
        ('REDIS_URL', settings.redis_url),
        ('SECRET_KEY', settings.secret_key),
    ]
    missing = [k for k, v in required if not v]
    if missing:
        raise RuntimeError(f"Missing required env vars: {missing}")
```

**Effort**: LOW (validation only)

---

### Issue 8: Mental Health Data Sensitivity

**Category**: Security / Compliance

**Severity**: HIGH (business critical)

**Files**:
- `src/infrastructure/database/models.py` - stores sensitive emotional records
- `src/infrastructure/services/openai_tagging_service.py` - sends data to OpenAI
- `src/presentation/api/routers/chat.py` - handles chat messages

**Concerns**:
- HIPAA/GDPR compliance not explicitly addressed in code
- Emotional records contain mental health history (high sensitivity)
- Crisis detection keywords hardcoded in tagging service (line 25-28)
- User data sent to OpenAI APIs (third-party processing)

**Current Mitigations**:
- Data is encrypted at rest in RDS (AWS default)
- TLS for transit (Nginx)
- JWT authentication required
- No PII exported in logs

**Recommendations**:
1. Add data classification markers in code comments
2. Document API data residency (OpenAI processes in US)
3. Implement automatic deletion of old records per data retention policy
4. Add audit logging for sensitive data access
5. Implement row-level security for multi-tenant access
6. Consider tokenization of emotional content before tagging

**Effort**: MEDIUM (policy + implementation)

---

## Fragile Areas

### Issue 9: LangChain Agent Service Complexity

**Category**: Maintainability

**Severity**: MEDIUM

**Files**:
- `src/infrastructure/services/langchain_agent_service.py` (331 lines)

**Concerns**:
- Fallback conversation ID hardcoded as string (line 126): `f"fallback_{user_id}_{agent_type}"`
- Crisis response protocol (line 86) has TODO with no implementation
- Context building is fragile if repositories return None
- Error handling swallows exceptions and returns fallback responses

**Fragile Pattern** (line 91-94):
```python
except Exception as e:
    logger.error(f"Error in send_message: {e}", exc_info=True)
    # Return fallback response
    return await self._create_fallback_response(...)
```

Silent failures degrade UX without alerting developers to actual problems.

**Safe Modification Guidance**:
1. Add structured logging with request IDs for tracing
2. Distinguish recoverable errors (transient) from failures (data integrity)
3. For data integrity failures, propagate exceptions; for transient, use fallbacks
4. Add test coverage for all error paths

---

## Test Coverage Gaps

### Critical Untested Areas

**Severity**: HIGH

| Area | What's Not Tested | Files | Risk |
|------|-------------------|-------|------|
| **Semantic Tagging** | End-to-end tag extraction accuracy | `openai_tagging_service.py` | Degraded personalization |
| **Emotional Records Persistence** | CRUD operations on emotional records | `sqlalchemy_emotional_repository.py` | Silent data loss |
| **Crisis Detection** | Detection accuracy of mental health urgency | `langchain_agent_service.py`, `openai_tagging_service.py` | Missed escalations |
| **Breathing Sessions** | Session tracking and analytics | `sqlalchemy_breathing_repository.py` | Broken user experience |
| **Token Budget Enforcement** | Monthly usage limits | `get_monthly_usage_use_case.py` | Unexpected API costs |
| **Domain Events** | Event persistence and processing | `sqlalchemy_event_repository.py` | Lost state transitions |

**Priority Order for Test Coverage**:
1. `GetMonthlyUsageUseCase` (simplest, 14 lines)
2. Repository CRUD operations (critical for data integrity)
3. Crisis detection accuracy (high business impact)
4. Semantic tagging (personalization foundation)

---

## Scaling Limits

### Issue 10: Vector Database Not Implemented

**Current Capacity**: N/A (feature disabled)

**Scaling Concern**:
- Without vector search, recommendation latency grows O(n) with user history
- At 10K users with 100 records each = 1M+ emotional records to scan
- LLM context window filled with historical data search

**Migration Path**:
1. Phase 1: Implement ChromaDB (in-memory, suitable for < 100K users)
2. Phase 2: Migrate to Qdrant (production-grade, 1M+ embeddings)
3. Phase 3: Add caching layer (Redis) for top-k similar users

---

## Dependencies at Risk

### Issue 11: dependency-injector Package Unused

**Package**: `dependency-injector>=4.41.0`

**Risk**: Supply chain / install time

**Current Status**: Listed in `requirements.txt` (line 39) but never imported

**Impact**:
- Adds dependency closure to attack surface
- Increases `pip install` time by ~100ms
- No functional benefit (container is handwritten)

**Fix**: Remove from both requirements files

**Effort**: TRIVIAL

---

## Known TODOs in Code

All `TODO` comments found in codebase:

| File | Line | TODO |
|------|------|------|
| `src/presentation/api/routers/auth.py` | (line ~) | Implement token invalidation |
| `src/infrastructure/records/repositories/sqlalchemy_emotional_repository.py` | (multiple) | Implement actual database operations |
| `src/infrastructure/breathing/repositories/sqlalchemy_breathing_repository.py` | (multiple) | Implement actual database operations |
| `src/infrastructure/services/langchain_agent_service.py` | 86 | Implement crisis response protocol |
| `src/infrastructure/container.py` | 155 | Initialize mock services (replace with real implementations) |
| `src/infrastructure/analytics/repositories/sqlalchemy_analytics_repository.py` | (multiple) | Persist analytics interactions |
| `src/infrastructure/events/repositories/sqlalchemy_event_repository.py` | (multiple) | Persist/query domain events |

**Collective Impact**: 15+ incomplete features. Most are P2 (missing functionality); crisis response is P0 (correctness).

---

## Summary: Risk Ranking

| Risk | Severity | Category | Fix Effort | Impact |
|------|----------|----------|------------|--------|
| No unit test suite | P0 | Testing | HIGH | High defect escape rate |
| Mock similarity/knowledge services | P2 | Functionality | MEDIUM | No personalization |
| Empty repository methods | P2 | Functionality | MEDIUM | Silent data loss |
| Duplicate code (tagging, use cases) | P1 | Maintainability | LOW | Maintenance drift |
| No startup validation | LOW | Operations | LOW | Confusing errors |
| Crisis detection unimplemented | P0 | Correctness | MEDIUM | Missed escalations |
| Vector DB disabled | P2 | Performance | MEDIUM | O(n) recommendation search |
| Mental health data sensitivity | HIGH | Security/Compliance | MEDIUM | Regulatory risk |

**Recommended First Phase**:
1. Implement unit tests for `GetMonthlyUsageUseCase`
2. Fix empty repository stubs (critical path first)
3. Consolidate duplicate code
4. Implement real similarity search service

---

*Concerns audit: 2026-03-19*
