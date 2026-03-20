# AI Readiness Audit — EmotionAI study guide

## What is it and why do we use it here

This document is a structured technical assessment of the EmotionAI backend codebase,
written at the end of Phase 01 (Architecture Clearance and AI Readiness Audit) before
Milestone 3 (AI Engineering foundation) begins. It answers three questions:

1. What architecture problems existed and were found during this phase?
2. What was cleaned up and implemented during Phase 01?
3. What must still be done before M3 can ship real AI personalization?

This is the gate document for M3. M3 planning starts from the specific inventory here,
not from re-reading the codebase. Every M3 prerequisite has a file path, a task
description, and an estimated complexity.

---

## What Was Found

The audit reviewed every layer of the Clean Architecture stack — domain, application,
infrastructure, and presentation — looking for dead files, broken abstractions, stub
implementations, and missing data infrastructure for AI personalization.

### Duplicate Files

**Root-level `agent_chat_use_case.py`**
- File: `src/application/use_cases/agent_chat_use_case.py`
- Status: Already deleted before Phase 01 (cleaned up in Milestone 1 slice 1.3)
- Canonical location: `src/application/chat/use_cases/agent_chat_use_case.py`

**Duplicate `tagging_service.py`**
- File: `src/application/services/tagging_service.py` — root-level shim, 3 lines
- File: `src/application/tagging/services/tagging_service.py` — feature-scoped with full ABC
- Severity: P1 — two canonical locations for the same interface confuses imports
- Status: Resolved in 01-01

**Duplicate `openai_tagging_service.py`**
- File: `src/infrastructure/services/openai_tagging_service.py` — old location, missing OTEL
- File: `src/infrastructure/tagging/services/openai_tagging_service.py` — feature-scoped, canonical
- Severity: P1 — old file lacked OTEL spans; stale copy
- Status: Resolved in 01-01

### Auth Dependency Indirection

**deps.py re-exported get_current_user_id**
- File: `src/presentation/api/routers/deps.py`
- Issue: A 4-line wrapper function re-exported `get_current_user_id` from
  `src/presentation/dependencies.py`, creating an unnecessary indirection layer.
  All 8 routers (auth, breathing, chat, data, dev_seed, records, usage) plus `main.py`
  imported through the wrapper.
- Severity: P2 — maintenance risk; renaming `dependencies.py` would require two-location
  updates instead of one
- Status: Resolved in 01-01

### Removed Dead Dependency

**`dependency-injector>=4.41.0` in requirements.txt**
- File: `requirements.txt` and `requirements-production.txt`
- Issue: Package never imported anywhere in the codebase. Pure dead weight pulling in
  a dependency with its own transitive graph.
- Severity: P1 — false signal to anyone reading requirements.txt
- Status: Resolved in Milestone 1 slice 1.1 (pre-Phase 01)

### Stub Repositories (4 total)

All four infrastructure repositories below had TODO stubs that returned `None` or `[]`
for every method. Any code path through these repos silently returned empty data.

**`src/infrastructure/records/repositories/sqlalchemy_emotional_repository.py`**
- Methods stubbed: `get_by_user_id`, `save`, `get_emotional_patterns`
- Severity: P0 — emotional records are core domain data; AgentChatUseCase reads these
  to build LangChain context
- Status: Resolved in 01-02

**`src/infrastructure/breathing/repositories/sqlalchemy_breathing_repository.py`**
- Methods stubbed: `get_by_user_id`, `save`, `get_session_analytics`
- Severity: P1 — breathing sessions not readable by any code path
- Status: Resolved in 01-02

**`src/infrastructure/analytics/repositories/sqlalchemy_analytics_repository.py`**
- Methods stubbed: `save_agent_interaction`
- Additional finding: No `AgentInteractionModel` ORM table exists. The
  `IAnalyticsRepository.save_agent_interaction` interface has no backing table.
- Severity: P2 — analytics are append-only logs; log-only implementation is acceptable
  for now but a persistent table is needed for M3 analytics queries
- Status: Partially resolved in 01-02 (structured logger.info used as interim solution)

**`src/infrastructure/events/repositories/sqlalchemy_event_repository.py`**
- Methods stubbed: `save_event`, `get_events_by_user`, `get_pending_events`,
  `mark_event_processed`
- Severity: P1 — domain events never persisted
- Status: Resolved in 01-02

### Mock Services Wired in Production Container

The production `ApplicationContainer` initializes two services that return hardcoded
mock data for every call:

**`MockSimilaritySearchService`**
- File: `src/infrastructure/services/mock_similarity_search_service.py`
- Container wire: `src/infrastructure/container.py` line 159
  ```python
  similarity_search_service = MockSimilaritySearchService()
  ```
- Effect: `find_similar_content()` returns `[]`. `find_similar_emotional_patterns()`
  returns `[]`. Semantic memory is entirely absent from the chat pipeline.
- Severity: P0 for M3 — this MUST be replaced before M3 personalization works
- Status: Remains in place (M3 prerequisite)

**`MockUserKnowledgeService`**
- File: `src/infrastructure/services/mock_user_knowledge_service.py`
- Container wire: `src/infrastructure/container.py` line 158
  ```python
  user_knowledge_service = MockUserKnowledgeService()
  ```
- Effect: `get_user_profile()` returns `None`. `get_personalization_context()` returns
  `{"mock_service": True}`. No tag aggregation happens even though tags are extracted.
- Severity: P0 for M3 — tag pipeline writes tags but never reads them back into context
- Status: Remains in place (M3 prerequisite)

### pgvector Not in Infrastructure

Before Phase 01 plan 03:
- `docker-compose.yml` used `postgres:13` image without pgvector extension
- `requirements.txt` had no `pgvector` entry
- `MessageModel` and `EmotionalRecordModel` had no `embedding_vector` column
- No Alembic migration enabling the vector extension

Severity: P0 for M3 — semantic search via pgvector cannot run without schema support.
Status: Resolved in 01-03.

### Analytics ORM Table Missing

`IAnalyticsRepository.save_agent_interaction` has no backing ORM model. There is no
`AgentInteractionModel` or `agent_interactions` table in `src/infrastructure/database/models.py`.

- Severity: P2 — log-only solution works for observability but blocks SQL-based analytics
- M3 prerequisite: if M3 needs to query interaction history for personalization, a table
  must be created

### Crisis Response Protocol — TODO

**File:** `src/infrastructure/services/langchain_agent_service.py`, line 95

```python
if therapy_response.crisis_detected:
    logger.warning(f"Crisis detected for user {user_id} in {agent_type} session")
    span.set_attribute("crisis_detected", True)
    # TODO: Implement crisis response protocol
```

The crisis detection flag is set, logged, and traced, but no escalation action is taken.
No push notification, no crisis resource injection, no session flagging.

- Severity: P0 for M3 launch — mental health app shipping with a no-op crisis handler
  is a safety risk
- M3 prerequisite: implement crisis escalation before M3 ships to production

### OTEL Span Missing from Old Tagging Service

Before 01-01, `src/infrastructure/services/openai_tagging_service.py` (the old location)
had no OTEL instrumentation. The feature-scoped version at
`src/infrastructure/tagging/services/openai_tagging_service.py` did not yet have the
`emotionai.tagging.classify` span. This was fixed in 01-01 as part of tagging consolidation.

---

## What Was Fixed in This Phase

### Plan 01-01: Code Cleanup and Import Consolidation

**Tagging service consolidation:**
- Expanded `src/application/tagging/services/tagging_service.py` from a 3-line shim to
  the full 130-line `ITaggingService` ABC with `TagExtractionResult` dataclass
- Deleted `src/application/services/tagging_service.py` (root-level copy)
- Ported `emotionai.tagging.classify` OTEL span with all attributes (`input.length`,
  `llm.model`, `tagging.content_type`, `tagging.has_urgency_keywords`, `llm.total_tokens`,
  `tagging.tag_count`) to `src/infrastructure/tagging/services/openai_tagging_service.py`
- Deleted `src/infrastructure/services/openai_tagging_service.py` (old location)
- Updated `container.py` import to `.tagging.services.openai_tagging_service`

**Auth dependency consolidation:**
- Removed `get_current_user_id` wrapper from `src/presentation/api/routers/deps.py`
- Updated 7 routers (auth, breathing, chat, data, dev_seed, records, usage) to import
  `get_current_user_id` directly from `...dependencies`
- Updated `main.py` to import from `src.presentation.dependencies`

**Auto-fix deviation:** `tests/unit/test_tagging_spans.py` import path updated
from old location to new canonical location after deletion caused a collection error.

Commit: `6773d95`

### Plan 01-02: Repository Stub Implementations

**Emotional records repository (`src/infrastructure/records/repositories/sqlalchemy_emotional_repository.py`):**
- Replaced 3 TODO stubs with real `async with self.db.get_session()` implementations
- `get_by_user_id`: filters by `user_id`, supports optional `limit` and `days_back` params
- `save`: inserts `EmotionalRecordModel`, flushes, returns `_model_to_dict()`
- `get_emotional_patterns`: returns aggregated emotion counts with timestamp ranges

**Breathing repository (`src/infrastructure/breathing/repositories/sqlalchemy_breathing_repository.py`):**
- Replaced 3 TODO stubs; added `_model_to_dict` helper and sqlalchemy imports
- `get_by_user_id`, `save`, `get_session_analytics` all implemented

**Analytics repository (`src/infrastructure/analytics/repositories/sqlalchemy_analytics_repository.py`):**
- Replaced TODO with structured `logger.info("agent_interaction", extra={...})` using
  all relevant fields from the interaction payload
- Decision: no ORM table yet; log-only is sufficient for current M2 observability needs

**Events repository (`src/infrastructure/events/repositories/sqlalchemy_event_repository.py`):**
- Replaced 4 TODO stubs with full CRUD against `DomainEventModel`
- `save_event`, `get_events_by_user`, `get_pending_events`, `mark_event_processed`
- Added `_model_to_domain_event` mapper

19 unit tests added across 4 new test files in `tests/unit/infrastructure/`.

Commit: `80b9361`

### Plan 01-03: pgvector Infrastructure

**docker-compose.yml:**
- Changed db image from `postgres:13` to `pgvector/pgvector:pg16`

**requirements.txt:**
- Added `pgvector>=0.4.0`

**Alembic migration `migrations/versions/005_add_embedding_vectors.py`:**
- Enables `CREATE EXTENSION IF NOT EXISTS vector` (idempotent)
- Adds `embedding_vector vector(1536) nullable` to `messages` table
- Adds `embedding_vector vector(1536) nullable` to `emotional_records` table
- Vector dimension 1536 matches OpenAI `text-embedding-ada-002` output

**ORM models (`src/infrastructure/database/models.py`):**
- Added `from pgvector.sqlalchemy import Vector` import
- Added `embedding_vector = Column(Vector(1536), nullable=True)` to `MessageModel`
- Added `embedding_vector = Column(Vector(1536), nullable=True)` to `EmotionalRecordModel`

4 integration tests added in `tests/integration/test_pgvector_migration.py`.

Commit: `2db84df`

---

## M3 Prerequisites

These items MUST be addressed before M3 features can ship. Each entry includes the
file path, specific task, and estimated complexity (low/medium/high).

### P0 — Blocking M3 functionality

**1. Replace MockSimilaritySearchService with PgVectorSimilaritySearchService**
- File: `src/infrastructure/services/mock_similarity_search_service.py`
- Interface: `src/application/services/similarity_search_service.py` (`ISimilaritySearchService`)
- Task: Implement `ISimilaritySearchService` using pgvector cosine distance queries.
  `find_similar_content()` must query the `messages` or `emotional_records` tables using
  `<=>` operator on `embedding_vector`. Replace mock registration in
  `src/infrastructure/container.py` line 159.
- Complexity: medium
- Depends on: M3 prerequisite 3 (embedding pipeline) to have data to search

**2. Replace MockUserKnowledgeService with real tag aggregation**
- File: `src/infrastructure/services/mock_user_knowledge_service.py`
- Interface: `src/application/services/user_knowledge_service.py` (`IUserKnowledgeService`)
- Task: `get_user_profile()` must aggregate tags from `emotional_records.tags` and
  `messages.tags` JSONB columns for the given user, returning a `UserKnowledgeProfile`
  with `frequent_tags`, `tag_categories`, and `tag_trends`. The `user_profiles` ORM
  table (`src/infrastructure/database/models.py`, `UserProfileModel`) already exists
  as a persistence target for the aggregated data. Replace mock registration in
  `src/infrastructure/container.py` line 158.
- Complexity: medium

**3. Implement embedding generation pipeline**
- Files: new Celery task + new service
- Task: Create a Celery task in `src/infrastructure/tasks/` that:
  1. Receives a `(record_id, content, record_type)` payload
  2. Calls OpenAI `text-embedding-ada-002` embeddings API (`openai.embeddings.create`)
  3. Writes the resulting 1536-float vector to `embedding_vector` on the corresponding
     `MessageModel` or `EmotionalRecordModel` row
  This task should be triggered from `records.py` after `session.commit()`, similar to
  how `notify_new_record.delay()` is called today
  (see `src/presentation/api/routers/records.py` lines 282–283).
- Complexity: high — requires OpenAI API integration, async Celery pattern, DB write

**4. Implement crisis response protocol**
- File: `src/infrastructure/services/langchain_agent_service.py`, line 95
- Task: Replace the `# TODO: Implement crisis response protocol` comment with real
  escalation logic. At minimum: inject crisis resources into the response, set a flag
  on the active conversation, and enqueue a notification task. The `crisis_detected`
  boolean is already on `TherapyResponse` and is already being logged and traced.
- Complexity: medium

### P1 — Required for correct personalization

**5. Wire AgentPersonalityModel into LangChain agent context**
- File: `src/infrastructure/services/langchain_agent_service.py`,
  method `_build_agent_context()` (line 138)
- Issue: `AgentPersonalityModel` (`src/infrastructure/database/models.py` line 116) stores
  `agent_style`, `communication_tone`, `therapy_approach`, `mood_patterns`,
  `stress_triggers`, `coping_strategies`. None of these fields are queried or injected
  into the agent context. The `_build_agent_context()` method only reads `UserModel`
  fields via `_get_user_profile()`.
- Task: Query `AgentPersonalityModel` for the user in `_build_agent_context()` and add
  the personality fields to the `AgentContext` so the LLM prompt includes the user's
  preferred therapy approach and communication tone.
- Complexity: medium

**6. Wire UserProfileDataModel into LangChain agent context**
- File: `src/infrastructure/services/langchain_agent_service.py`,
  method `_get_user_profile()` (line 188)
- Issue: `_get_user_profile()` reads from `UserModel` (age, personality_type,
  therapy_goals, preferences) but `UserProfileDataModel`
  (`src/infrastructure/database/models.py` line 84) stores richer onboarding data:
  `personality_type` (MBTI), `relaxation_tools` (array), `selfcare_frequency`,
  `therapy_chat_history_preference`. These are never read.
- Task: Join or separately query `UserProfileDataModel` in `_get_user_profile()` and
  merge the results so the LangChain prompt has access to MBTI type and relaxation tools.
- Complexity: low-medium

### P2 — Optional for M3 but improves analytics

**7. Create AgentInteractionModel ORM table**
- File: `src/infrastructure/database/models.py`
- Task: Add an `AgentInteractionModel` with fields: `id`, `user_id`, `agent_type`,
  `conversation_id`, `tokens_used`, `therapeutic_approach`, `crisis_detected`,
  `created_at`. Create a new Alembic migration. Update
  `src/infrastructure/analytics/repositories/sqlalchemy_analytics_repository.py` to
  persist to the table instead of using `logger.info`.
- Complexity: low (model + migration + 5-line repo change)

---

## Personalization Gap Map

This table maps every endpoint and service to whether it currently uses the user's
profile data (`UserProfileDataModel`, `AgentPersonalityModel`) and what the specific gap is.
"Partial" means some user data flows through but key personalization fields are absent.

| Endpoint / Service | Uses user_profile? | Uses agent_personality? | Gap Description |
|---|---|---|---|
| `POST /v1/api/chat` via `LangChainAgentService._build_agent_context()` | Partial | No | Reads `UserModel.age`, `personality_type`, `therapy_goals`, `preferences` via `_get_user_profile()`. Does NOT query `UserProfileDataModel.relaxation_tools`, `selfcare_frequency`, or `UserProfileDataModel.personality_type` (MBTI). Does NOT query `AgentPersonalityModel` at all — `agent_style`, `communication_tone`, `therapy_approach`, `coping_strategies` are never loaded. |
| `POST /v1/api/chat` via `ISimilaritySearchService` (mock) | No | No | `MockSimilaritySearchService.find_similar_content()` returns `[]`. No semantic memory retrieval. Personalized context from past conversations is entirely absent. |
| `POST /v1/api/chat` via `IUserKnowledgeService` (mock) | No | No | `MockUserKnowledgeService.get_user_profile()` returns `None`. Tag aggregation from `user_profiles` table is never read. `get_personalization_context()` returns `{"mock_service": True}`. |
| `GET /v1/api/emotional_records/` | No | No | Returns raw `EmotionalRecordModel` rows ordered by timestamp. No personalization — response shape is identical for all users. |
| `POST /v1/api/emotional_records/` | No | No | Tags are extracted via `notify_new_record` Celery task (triggers `ITaggingService`) but the tags written back to `EmotionalRecordModel.tags` are never used to enrich the user profile in the same request. `MockUserKnowledgeService.update_user_profile_with_tags()` is a no-op. |
| `GET /v1/api/breathing_sessions/` | No | No | Returns raw `BreathingSessionModel` rows. No personalization. |
| `POST /v1/api/breathing_sessions/` | No | No | Session saved with no profile enrichment. Breathing patterns are not recommended based on user history. |
| `GET /v1/api/breathing_patterns/` | No | No | Returns global presets plus user-created patterns. No ranking or filtering by user preferences. |
| `GET /v1/api/profile` via `ProfileService` | Yes | Yes | Profile read fetches `UserProfileDataModel` and `AgentPersonalityModel` correctly. This endpoint works as expected. |
| `PUT /v1/api/profile` via `ProfileService` | Yes | Yes | Profile update persists to `UserProfileDataModel` and `AgentPersonalityModel`. This endpoint works as expected. |

---

## Embedding Readiness

This section assesses which data pipelines are structurally ready for pgvector queries
and what work remains before M3 can use them.

### messages table

- **Current status:** `embedding_vector vector(1536) nullable` column exists (added in
  migration 005). All existing rows have `embedding_vector = NULL`.
- **What's needed:** An async Celery task that calls `openai.embeddings.create(input=content,
  model="text-embedding-ada-002")` and writes the 1536-float vector to the column. The
  task should be triggered after each `MessageModel` insert in
  `src/infrastructure/conversations/repositories/sqlalchemy_conversation_repository.py`.
- **M3 effort:** High — requires OpenAI embedding API integration, Celery task wiring,
  DB update path. This is the primary M3 embedding task.
- **Blocking:** `PgVectorSimilaritySearchService` will be querying this table. Without
  populated vectors, semantic search returns no results.

### emotional_records table

- **Current status:** `embedding_vector vector(1536) nullable` column exists (added in
  migration 005). All existing rows have `embedding_vector = NULL`.
- **What's needed:** Same Celery task approach as messages, triggered after each
  `EmotionalRecordModel` insert (trigger point already exists in
  `src/presentation/api/routers/records.py` at the `_enqueue_record_notification` call,
  line 282). A separate embedding task can be enqueued from the same location.
- **M3 effort:** Medium — same pipeline as messages, just a different trigger point and
  content field (`emotion + notes` as the text to embed).
- **Blocking:** Semantic search over emotional history requires this data.

### breathing_sessions table

- **Current status:** No `embedding_vector` column. `BreathingSessionModel` was
  explicitly excluded from migration 005.
- **Assessment:** Breathing sessions contain low-information-density text (`pattern_name`,
  `notes`). Semantic search over breathing content has limited value — "box breathing"
  and "4-7-8 breathing" would produce similar embeddings. Session analytics are better
  served by structured queries (effectiveness_rating, duration_minutes, completed).
- **Recommendation:** Do NOT add embedding columns to breathing_sessions in M3.
  Use structured queries for breathing recommendations. Revisit after M3 if use case
  emerges.
- **M3 effort:** None required.

### user_profiles table

- **Current status:** `UserProfileModel` (`src/infrastructure/database/models.py` line 409)
  has no `embedding_vector` column. This table stores aggregated tag frequencies and
  personality insights.
- **Assessment:** Embedding the `personality_insights` and `behavioral_patterns` JSONB
  fields could enable user similarity clustering ("find users with similar emotional
  profiles"). This is a M3+ use case, not M3.0.
- **Recommendation:** Do NOT add embedding columns in M3. Implement in M3+ after the
  core RAG pipeline is working. Priority is message and emotional record embeddings first.
- **M3 effort:** Deferred.

### conversations table

- **Current status:** `ConversationModel` (`src/infrastructure/database/models.py` line 159)
  has no `embedding_vector` column. Conversations are containers for messages.
- **Assessment:** Embedding at the conversation level (a summary of all messages) is
  coarser than embedding at the message level. M3 RAG retrieval is better served by
  individual `MessageModel` embeddings retrieved with top-k similarity. Full conversation
  embedding would duplicate the message embedding effort for less retrieval precision.
- **Recommendation:** Do NOT add embedding columns to conversations. Individual message
  embeddings in the `messages` table are the correct target.
- **M3 effort:** None required.

---

## Further Reading

- `src/infrastructure/services/langchain_agent_service.py` — current agent context
  building logic; read before implementing M3 personalization wiring
- `src/infrastructure/database/models.py` — all ORM models including `AgentPersonalityModel`,
  `UserProfileDataModel`, `UserProfileModel` (tag aggregation target)
- `src/infrastructure/container.py` lines 157–159 — mock service wire points to replace
- `migrations/versions/005_add_embedding_vectors.py` — pgvector migration reference
- `src/application/services/similarity_search_service.py` — `ISimilaritySearchService`
  interface to implement with pgvector
- `src/application/services/user_knowledge_service.py` — `IUserKnowledgeService` interface
  to implement with real tag aggregation
- Milestone 3 plan in `ROADMAP.md` — official M3 scope and success criteria
