# EmotionAI — Backend Evolution Roadmap
> GSD spec-driven roadmap. Brownfield project — run `/gsd:map-codebase` before starting any milestone.

---

## Project context

EmotionAI is a production FastAPI + PostgreSQL + AWS backend for mental health tracking.
Clean Architecture (domain → application → infrastructure → presentation).
Stack: Python 3.11, FastAPI, asyncpg, SQLAlchemy 2.0, Alembic, LangChain, Redis, Docker.

**Owner goal:** evolve this codebase to demonstrate professional Python backend skills
and build a bridge toward AI Engineering. Every milestone must produce both
working code AND a `docs/learning/` study document explaining the tech added.

**Non-negotiable rule:** for every new technology introduced, Claude must write
`docs/learning/<technology>.md` explaining: what it is, why we use it here,
how it works conceptually, and the key patterns used in this project.

---

## Pre-flight: codebase investigation

Before planning any milestone, Claude must answer these questions by reading the repo:

```
INVESTIGATE:
1. Read src/infrastructure/container.py — how is DI wired? Which services are stubs?
2. Read src/presentation/api/routers/deps.py — confirm the auth bypass (hardcoded UUID fallback)
3. Check if tests/ directory exists. List all test files found.
4. Read requirements.txt and requirements-production.txt — confirm asyncpg, pytest-asyncio, pytest-cov are present
5. Read src/infrastructure/database/models.py — list all ORM models
6. Read src/infrastructure/services/ — which services are real vs mock stubs?
7. Read TECH_DEBT.md — list all P0 and P1 items
8. Check if docker-compose.yml exposes redis and postgres with correct ports for local testing
9. Look for any existing conftest.py or pytest.ini / pyproject.toml [tool.pytest] config
10. Read src/application/use_cases/ — list all use cases, identify the simplest one for first test
```

Write findings to `.planning/codebase/CONCERNS.md` before proceeding.

---

## Milestone 1 — Professional Python testing foundation

**Goal:** EmotionAI has a real unit test suite with >70% coverage on use cases and domain.
No regressions go undetected. A senior Python engineer reads the tests and says
"this team knows what they're doing."

**Success criteria (verifiable):**
- [ ] `pytest --cov=src --cov-report=term-missing` runs without errors
- [ ] Coverage on `src/application/` is ≥ 70%
- [ ] Coverage on `src/domain/` is ≥ 80%
- [ ] All tests run in < 10 seconds (no real DB or network calls)
- [ ] `docs/learning/pytest_fastapi.md` exists and covers: venv setup, pytest-asyncio, TestClient, mocking with unittest.mock, coverage reports
- [ ] `docs/learning/clean_architecture_testing.md` exists and explains: how to test each layer independently, why domain tests need no mocks, why use case tests mock the repo interface

**Slices:**

### 1.1 — Test infrastructure setup
Research: read existing test files, conftest.py if any, pyproject.toml.
Tasks:
- Create `pyproject.toml` with `[tool.pytest.ini_options]` (testpaths, asyncio_mode=auto) and `[tool.coverage.run]` (source=src, omit=migrations/*)
- Create `tests/conftest.py` with: async engine fixture (SQLite in-memory), mock ApplicationContainer factory, mock repository base class
- Verify `pytest -q` runs (0 tests, no errors)
- Write `docs/learning/pytest_fastapi.md`

### 1.2 — Domain entity tests
Research: read all files in `src/domain/entities/` and `src/domain/`.
Tasks:
- Write unit tests for every domain entity (pure Python, zero mocks needed)
- Write unit tests for every value object and domain exception
- Target: 100% coverage on `src/domain/`
- Add section to `docs/learning/clean_architecture_testing.md`: "Testing the domain layer"

### 1.3 — Use case tests with mocked repositories
Research: read `src/application/use_cases/` and `src/application/chat/use_cases/`. Also check TECH_DEBT.md P1 — duplicate use case file.
Tasks:
- Fix P1 debt: resolve duplicate `agent_chat_use_case.py` (verify, update imports, delete root-level copy)
- Write use case tests using `AsyncMock` for repository interfaces
- Cover happy path + 2 error paths per use case
- Start with `GetMonthlyUsageUseCase` (simplest), then `AgentChatUseCase`
- Add section to `docs/learning/clean_architecture_testing.md`: "Testing use cases"

### 1.4 — FastAPI router integration tests
Research: read `src/presentation/api/routers/` — focus on auth.py, health.py, records.py.
Tasks:
- Create `tests/integration/` with `TestClient` tests for: /health, /auth/register, /auth/login, /auth/refresh
- Mock the ApplicationContainer at the FastAPI dependency level (not at DB level)
- Fix P0 debt: remove hardcoded UUID auth bypass in deps.py (or document it clearly as test-only)
- Add section to `docs/learning/pytest_fastapi.md`: "Integration testing FastAPI with TestClient"

---

## Milestone 2 — Observability and async task infrastructure

**Goal:** EmotionAI has production-grade observability (metrics + tracing) and an
async task queue. Anyone reviewing this project says "this is how you operate a
real Python backend."

**Success criteria (verifiable):**
- [ ] `GET /metrics` returns Prometheus-formatted metrics (request count, latency histogram, active connections)
- [ ] A Celery worker starts with `celery -A src.infrastructure.tasks.worker worker --loglevel=info`
- [ ] At least one background task (email/notification stub) is triggered from a FastAPI endpoint
- [ ] OpenTelemetry spans appear in Jaeger UI at `localhost:16686` when running docker-compose
- [ ] All tests from Milestone 1 still pass
- [ ] `docs/learning/prometheus_fastapi.md` exists: what metrics are, push vs pull, histogram vs counter vs gauge, how to instrument FastAPI
- [ ] `docs/learning/celery_redis.md` exists: task queue concepts, broker vs backend, worker lifecycle, idempotency, retry strategies
- [ ] `docs/learning/opentelemetry.md` exists: traces vs metrics vs logs, spans, context propagation, why OTEL beats vendor-specific SDKs

**Slices:**

### 2.1 — Prometheus instrumentation
Status: Completed on 2026-03-19 via `m2s1-01`

Research: read `src/presentation/api/main.py` (middleware stack), `requirements-production.txt`.
Tasks:
- Add `prometheus-fastapi-instrumentator` to requirements
- Wire Prometheus middleware in `main.py` — expose `/metrics` endpoint
- Add 3 custom business metrics: `emotionai_chat_requests_total`, `emotionai_active_users_gauge`, `emotionai_openai_latency_seconds`
- Add Prometheus + Grafana services to `docker-compose.yml` with a basic dashboard JSON
- Write `docs/learning/prometheus_fastapi.md`

### 2.1.1 — Demo flow hardening for E2E learning path (INSERTED)
Status: Pending (inserted 2026-03-19)

Research: review `scripts/demo_flow.sh`, API route contracts for `/metrics`, and upcoming observability endpoints (Celery/Flower + OTEL/Jaeger) to keep one durable E2E learning path.
Tasks:
- Refactor `scripts/demo_flow.sh` into step-based checks reusable per feature slice
- Add metrics verification path (`/metrics` availability + key collector assertions)
- Define extension points so future slices append checks (Celery/Flower now, telemetry/Jaeger later) without script rewrites
- Ensure script outputs actionable pass/fail diagnostics for learning and demos

### 2.2 — Celery + Redis task queue
Research: read `src/infrastructure/container.py` (Redis wiring), `docker-compose.yml` (Redis service).
Tasks:
- Create `src/infrastructure/tasks/` package with: `worker.py` (Celery app), `notification_tasks.py` (stub task), `__init__.py`
- Register Celery app in `container.py`
- Add a `/v1/api/records` endpoint hook that fires a background task after a new record is saved
- Add `celery` and `flower` to docker-compose for local monitoring
- Write `docs/learning/celery_redis.md`

### 2.3 — OpenTelemetry tracing
Research: read all routers and the LangChain agent service — identify the slowest call chains.
Tasks:
- Add `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp` to requirements
- Auto-instrument FastAPI (zero-code instrumentation)
- Add manual spans around: LangChain agent call, OpenAI tagging call, DB queries in critical use cases
- Add Jaeger to `docker-compose.yml`
- Write `docs/learning/opentelemetry.md`

---

## Milestone 3 — AI Engineering foundation

**Goal:** EmotionAI has a real semantic memory system (not mock stubs) and a RAG
pipeline over the user's emotional history. This demonstrates production AI
engineering skills — not just calling the OpenAI API, but building retrieval,
embeddings, and context management properly.

**Success criteria (verifiable):**
- [ ] `ISimilaritySearchService` is implemented with pgvector (not mock stub)
- [ ] `POST /v1/api/chat` uses real semantic context retrieval from user's history
- [ ] `GET /v1/api/chat/search?q=<query>` returns semantically similar past records
- [ ] Embeddings are generated async and stored in a `vector_embeddings` table (new migration)
- [ ] MLflow tracking server runs at `localhost:5000` via docker-compose and logs at least one experiment
- [ ] All tests from Milestones 1–2 still pass
- [ ] `docs/learning/pgvector_embeddings.md` exists: what embeddings are, cosine similarity, how pgvector extends PostgreSQL, when to use pgvector vs Qdrant
- [ ] `docs/learning/rag_langchain.md` exists: what RAG is, retriever patterns, prompt construction, context window management, hallucination reduction
- [ ] `docs/learning/mlflow.md` exists: experiment tracking, runs, metrics, artifacts, model registry, how it compares to TensorBoard

**Slices:**

### 3.1 — pgvector semantic memory (replace mock stub)
Research: read `src/infrastructure/services/mock_similarity_search_service.py`, `src/application/services/` (ISimilaritySearchService interface), `settings.py` (vector DB config), existing SQLAlchemy models.
Tasks:
- Enable pgvector extension in a new Alembic migration (`alembic revision --autogenerate -m "add_vector_embeddings_table"`)
- Add `vector_embeddings` table to models: `id`, `user_id`, `source_type` (record/chat/profile), `source_id`, `embedding` (vector(1536)), `content_preview`, `created_at`
- Implement `PgVectorSimilaritySearchService` replacing the mock — use `openai.embeddings.create` async
- Wire the real implementation in `container.py`
- Write `docs/learning/pgvector_embeddings.md`

### 3.2 — RAG pipeline over emotional history
Research: read `src/infrastructure/services/langchain_agent_service.py` — understand how context is currently built for the agent. Read `src/domain/entities/user.py` behavioral profile.
Tasks:
- Create `src/application/chat/use_cases/rag_context_builder.py` — given user_id + query, retrieve top-k relevant records/memories via pgvector
- Inject RAG context into the LangChain agent's system prompt (replace or augment current context building)
- Add `GET /v1/api/records/search?q=<semantic_query>` endpoint
- Add embedding generation as a Celery task (triggered after new record or chat message saved)
- Write `docs/learning/rag_langchain.md`

### 3.3 — MLflow experiment tracking
Research: check if any model training exists in the codebase. If not, create a standalone experiment script.
Tasks:
- Add MLflow service to `docker-compose.yml` with SQLite backend and S3-compatible artifact store
- Create `scripts_emotionai/ml_experiments/emotion_classifier.py` — simple sklearn classifier on mood labels, tracked with MLflow (params, metrics, confusion matrix artifact)
- Add `mlflow.set_tracking_uri()` config to `settings.py`
- Document how to view experiments: `mlflow ui --port 5000`
- Write `docs/learning/mlflow.md`

---

## Learning documentation index

All study docs go in `docs/learning/`. Claude must create or update these alongside
the relevant milestone slice — never at the end, always as part of the task.

```
docs/learning/
├── pytest_fastapi.md          (Milestone 1)
├── clean_architecture_testing.md  (Milestone 1)
├── prometheus_fastapi.md      (Milestone 2)
├── celery_redis.md            (Milestone 2)
├── opentelemetry.md           (Milestone 2)
├── pgvector_embeddings.md     (Milestone 3)
├── rag_langchain.md           (Milestone 3)
└── mlflow.md                  (Milestone 3)
```

Each learning doc must follow this structure:
```markdown
# <Technology> — EmotionAI study guide

## What is it and why do we use it here
## How it works conceptually (explain as if to a junior developer)
## Key patterns used in this project (with code examples from the actual codebase)
## Common mistakes and how to avoid them
## Further reading
```

---

## Tech debt resolved per milestone

| Item | Milestone | File |
|---|---|---|
| No unit test suite (P0) | 1 | test_integration.py |
| Duplicate agent_chat_use_case.py (P1) | 1.3 | src/application/ |
| Auth bypass hardcoded UUID (P0) | 1.4 | deps.py |
| Mock similarity search stub (P2) | 3.1 | mock_similarity_search_service.py |
| dependency-injector unused (P1) | 1.1 | requirements.txt |

---

## How to start with GSD

```bash
# 1. Install GSD if not already installed
npx gsd install

# 2. Map the codebase first (mandatory for brownfield)
/gsd:map-codebase

# 3. Review the concerns file Claude generates
cat .planning/codebase/CONCERNS.md

# 4. Start Milestone 1
/gsd:discuss-phase
# → tell Claude: "start with Milestone 1, slice 1.1"

# 5. Let GSD plan and execute
/gsd:plan
/gsd:execute
```

**Important:** tell Claude at the start of every session:
> "This is a learning-focused project. For every new technology you introduce,
> write the corresponding docs/learning/<tech>.md study guide as part of the slice,
> not as an afterthought. I want to understand what I'm building, not just ship it."
