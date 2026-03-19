---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: m2s1.1 — Demo Flow Hardening (INSERTED)
status: pending
last_updated: "2026-03-19T13:03:35.189Z"
progress:
  total_phases: 8
  completed_phases: 5
  total_plans: 10
  completed_plans: 5
---

# Project State

## Current Position

**Milestone:** 2 — Observability and async task infrastructure
**Current Phase:** m2s1.1 — Demo Flow Hardening (INSERTED)
**Status:** m2s1 complete; urgent inserted phase pending planning

## Phase Progress

| Phase | Name | Status |
|-------|------|--------|
| m1s1 | Test Infrastructure Setup | ● Complete (1/1 plan done) |
| m1s2 | Domain Entity Tests | ● Complete (1/1 plan done) |
| m1s3 | Use Case Tests | ● Complete (1/1 plan done) |
| m1s4 | Router Integration Tests | ● Complete (1/1 plan done) |
| m2s1 | Prometheus Instrumentation | ● Complete (1/1 plan done) |
| m2s1.1 | Demo flow hardening for E2E learning path (INSERTED) | ○ Pending (0/0 plans done) |
| m2s2 | Celery + Redis Task Queue | ○ Pending (0/3 plans done) |
| m2s3 | OpenTelemetry Tracing | ○ Pending (0/2 plans done) |

## Accumulated Context

### Roadmap Evolution
- Phase m2s1.1 inserted after Phase m2s1: Improve `scripts/demo_flow.sh` each feature/tool to harden E2E learning path (metrics now, telemetry next) (URGENT)

### Codebase Facts
- Python 3.11, FastAPI, asyncpg, SQLAlchemy 2.0
- Clean Architecture: domain → application → infrastructure → presentation
- Composition root: `src/infrastructure/container.py` (ApplicationContainer)
- `tests/` directory has conftest.py, __init__.py in all subdirs; ready for test slices
- pyproject.toml created with asyncio_mode=auto, coverage source=src, branch=true
- requirements.txt: aiosqlite>=0.19.0 added, dependency-injector removed
- Prometheus `/metrics` is exposed from FastAPI lifespan via `app.state.instrumentator`
- Custom metrics live in `src/infrastructure/metrics/custom_metrics.py`
- Local observability stack now includes Prometheus scrape config and Grafana provisioning
- aiosqlite 0.22.1 installed in .venv
- Duplicate agent_chat_use_case.py TECH_DEBT: root copy at src/application/use_cases/ does NOT exist (already cleaned up); canonical at src/application/chat/use_cases/agent_chat_use_case.py
- deps.py (src/presentation/api/routers/deps.py) is clean — no hardcoded UUID bypass; uses JWT via src/presentation/dependencies.py

### Key Files
- `src/infrastructure/container.py` — DI root, mock factory should mirror its interface
- `src/domain/entities/user.py`, `src/domain/entities/agent_personality.py`
- `src/domain/value_objects/user_profile.py`
- `src/domain/events/domain_events.py`
- `src/application/usage/use_cases/get_monthly_usage_use_case.py`
- `src/application/chat/use_cases/agent_chat_use_case.py`
- `src/presentation/api/routers/` — health.py, auth.py, records.py
- `src/infrastructure/metrics/custom_metrics.py`
- `prometheus/prometheus.yml`
- `grafana/provisioning/dashboards/emotionai.json`

### Decisions Made
- No fail_under threshold in coverage config until slice 1.2 (domain tests) ships
- Learning doc (pytest_fastapi.md) grows with slices — stub in 1.1, TestClient section in 1.4, mocking in 1.3
- asyncio_mode = auto in pytest config
- branch coverage enabled from start
- aiosqlite must be added to requirements.txt for async SQLite fixture
- [Phase m1s1]: No fail_under coverage threshold until slice 1.2 ships domain tests
- [Phase m1s1]: TestBase kept separate from production Base — production ORM uses PostgreSQL-specific UUID/JSONB types incompatible with SQLite
- [Phase m1s1]: dependency-injector removed from requirements.txt — confirmed unused
- [Phase m1s2-domain-entity-tests]: xfail(strict=True) used for 2 domain bugs: update_profile() crashes and is_profile_complete() returns None — bugs documented, not hidden
- [Phase m1s2-domain-entity-tests]: coverage exclude_lines added for @abstractmethod and frozen dataclass dead branches — 2 genuinely unreachable lines remain
- [Phase m1s3]: DB suggestion persistence path in AgentChatUseCase left uncovered at unit level — belongs in integration test, not mock-based test
- [Phase m1s3]: make_use_case(**kwargs) helper pattern established for multi-dependency use case construction
- [Phase m1s4]: Health endpoint is at /health/ (trailing slash) due to redirect_slashes=False on both router and app
- [Phase m1s4]: passlib+bcrypt incompatibility patched in test fixtures via pwd_context.hash/verify override — production issue deferred
- [Phase m1s4]: Auth router returns 400 (not 422) for missing fields — tests assert 400 to match actual router behaviour
- [Phase m2s1-prometheus-instrumentation]: Stored the Prometheus Instrumentator on app.state and exposed /metrics during lifespan startup.
- [Phase m2s1-prometheus-instrumentation]: Pre-initialized bounded labelsets so labeled metric families appear in /metrics before the first chat request.
- [Phase m2s1-prometheus-instrumentation]: Used track_inprogress() to represent active users as concurrent in-flight chat handlers.

## Issues / Blockers

- Full regression suite still exits non-zero because three pre-existing `XPASS(strict)` domain tests now pass unexpectedly in `tests/domain/test_user.py`. These were carried forward from Milestone 1 and are not regressions from m2s1.
- Docker smoke verification for Prometheus/Grafana could not run in this environment because the Docker daemon is unavailable at `/var/run/docker.sock`.

## Last Updated
2026-03-19T11:57:00Z — Completed m2s1-01-PLAN.md (Prometheus instrumentation)
