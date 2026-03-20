---
phase: 01
slug: architecture-clearance-ai-readiness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `python -m pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-cleanup | cleanup | 1 | duplicate removal | manual grep | `grep -r "from src.application.services.tagging_service" src/ \| wc -l` | N/A | pending |
| 01-emotional-repo | repo stubs | 2 | SQLAlchemy impl | unit | `python -m pytest tests/unit/infrastructure/test_emotional_repository.py -v` | W0 | pending |
| 01-breathing-repo | repo stubs | 2 | SQLAlchemy impl | unit | `python -m pytest tests/unit/infrastructure/test_breathing_repository.py -v` | W0 | pending |
| 01-analytics-repo | repo stubs | 2 | SQLAlchemy impl | unit | `python -m pytest tests/unit/infrastructure/test_analytics_repository.py -v` | W0 | pending |
| 01-events-repo | repo stubs | 2 | SQLAlchemy impl | unit | `python -m pytest tests/unit/infrastructure/test_event_repository.py -v` | W0 | pending |
| 01-pgvector-migration | pgvector | 2 | schema migration | integration | `python -m pytest tests/integration/test_pgvector_migration.py -v` | W0 | pending |
| 01-audit-doc | audit doc | 3 | docs written | manual | `test -f docs/learning/ai_readiness_audit.md && wc -l docs/learning/ai_readiness_audit.md` | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/infrastructure/test_emotional_repository.py` — unit tests for emotional repo (created by plan 01-02 Task 1)
- [ ] `tests/unit/infrastructure/test_breathing_repository.py` — unit tests for breathing repo (created by plan 01-02 Task 1)
- [ ] `tests/unit/infrastructure/test_analytics_repository.py` — unit tests for analytics repo (created by plan 01-02 Task 2)
- [ ] `tests/unit/infrastructure/test_event_repository.py` — unit tests for events repo (created by plan 01-02 Task 2)
- [ ] `tests/integration/test_pgvector_migration.py` — ORM metadata verification for pgvector columns (created by plan 01-03 Task 3)

*Existing conftest.py + AsyncSession fixtures cover all test infrastructure needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| No dangling imports after duplicate removal | duplicate removal | File deletion side effects not testable with pytest | `grep -r "from src.application.services.tagging_service" src/` returns 0 results |
| docker-compose pgvector image starts cleanly | pgvector infra | Docker startup not in CI | `docker-compose up -d db && docker-compose exec db psql -U postgres -c "SELECT extversion FROM pg_extension WHERE extname='vector';"` |
| Alembic upgrade head applies cleanly | pgvector migration | Requires running pgvector-enabled Postgres | `docker-compose up -d db && alembic upgrade head` |
| ai_readiness_audit.md has all required sections | audit doc | Section presence not unit-testable | `grep -c "## " docs/learning/ai_readiness_audit.md` >= 5 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
