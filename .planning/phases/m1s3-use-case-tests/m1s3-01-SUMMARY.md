---
phase: m1s3-use-case-tests
plan: 01
subsystem: testing
tags: [pytest, asyncmock, use-cases, clean-architecture, application-layer]

requires:
  - phase: m1s2-domain-entity-tests
    provides: domain layer tests, conftest.py MockApplicationContainer, pyproject.toml asyncio_mode=auto

provides:
  - 18 passing use case tests (7 GetMonthlyUsageUseCase + 11 AgentChatUseCase)
  - 100% coverage on GetMonthlyUsageUseCase
  - 72% coverage on AgentChatUseCase (core paths covered; DB suggestion path is infrastructure-level)
  - docs/learning/clean_architecture_testing.md "Testing Use Cases" section

affects:
  - m1s4-router-integration-tests
  - any future use case changes

tech-stack:
  added: []
  patterns:
    - "make_use_case() helper: defaults + override kwargs for multi-dependency use case construction"
    - "AsyncMock injection: interface boundary replaced with AsyncMock, no real I/O"
    - "patch datetime.now(): freeze current time for default year/month tests"
    - "best-effort path testing: verify side-effect failures don't abort primary response"

key-files:
  created:
    - tests/application/usage/use_cases/test_get_monthly_usage_use_case.py
    - tests/application/chat/use_cases/test_agent_chat_use_case.py
  modified:
    - docs/learning/clean_architecture_testing.md

key-decisions:
  - "Suggestion persistence path (lines 104-134 in AgentChatUseCase) left uncovered — it requires a real DatabaseConnection session and belongs in an integration test, not a unit test"
  - "make_use_case() helper used for AgentChatUseCase (11 constructor params) — avoids 10+ lines of mock setup per test"
  - "asyncio_mode=auto from pyproject.toml means no @pytest.mark.asyncio decorators needed"
  - "Token logging path tested both happy-path (assert called_once) and failure-path (assert response returned despite exception)"

requirements-completed: []

duration: 3min
completed: 2026-03-19
---

# Phase m1s3 Plan 01: Use Case Tests Summary

**18 AsyncMock-based use case tests covering GetMonthlyUsageUseCase (7 tests, 100% coverage) and AgentChatUseCase (11 tests) including happy paths, crisis detection, token logging, and best-effort resilience**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-19T09:37:42Z
- **Completed:** 2026-03-19T09:40:15Z
- **Tasks:** 3 (Task 1 was no-op — duplicate already resolved)
- **Files modified:** 3

## Accomplishments

- 7 GetMonthlyUsageUseCase tests: happy path, zero usage for new user, argument forwarding, default year/month via `datetime.now()` patch, explicit args override defaults, exception propagation, single-call guarantee
- 11 AgentChatUseCase tests: happy path, argument forwarding (user_id/agent_type/message/context), None context → empty dict, crisis_detected=True passthrough, crisis_detected=False passthrough, agent failure re-raise, missing `send_message` AttributeError, token logging with metadata, token logging skipped when repo=None, skipped when tokens_total=0, logging failure does not abort response
- `docs/learning/clean_architecture_testing.md` extended with "Testing Use Cases" section: AsyncMock pattern, make_use_case() helper, best-effort path testing, what NOT to test

## Task Commits

1. **Task 1: Resolve duplicate agent_chat_use_case.py** — no-op (already resolved per STATE.md), no commit
2. **Task 2: GetMonthlyUsageUseCase tests** — `1900138` (test)
3. **Task 3: AgentChatUseCase tests + learning doc** — `b533a0e` (test + docs)

## Files Created/Modified

- `tests/application/usage/use_cases/test_get_monthly_usage_use_case.py` — 7 tests: delegation, defaults, interaction verification, error propagation
- `tests/application/chat/use_cases/test_agent_chat_use_case.py` — 11 tests: happy path, crisis, failure, token logging resilience
- `docs/learning/clean_architecture_testing.md` — appended "Testing Use Cases" section (~90 lines)

## Coverage Results

| File | Coverage | Notes |
|---|---|---|
| `get_monthly_usage_use_case.py` | 100% | Full coverage — simple delegation with defaults |
| `agent_chat_use_case.py` | 72% | Core paths covered; DB suggestion path (lines 104-134) needs integration test |

## Decisions Made

- Suggestion persistence path (lines 104-134 in `agent_chat_use_case.py`) left uncovered at unit test level: it uses `self.database.get_session()` which requires a real async DB session — this is infrastructure-level behaviour and belongs in an integration test, not a mock-based use case test
- `make_use_case(**kwargs)` helper pattern established for complex constructors: set all mocked defaults once, override per-test
- Token logging best-effort tests are important for mental health UX: a logging failure must never prevent the AI response from reaching the user

## Deviations from Plan

None — plan executed exactly as written. Task 1 confirmed no-op (no duplicate file).

## Self-Check

- [x] `tests/application/usage/use_cases/test_get_monthly_usage_use_case.py` exists
- [x] `tests/application/chat/use_cases/test_agent_chat_use_case.py` exists
- [x] `docs/learning/clean_architecture_testing.md` updated
- [x] Commit `1900138` exists (GetMonthlyUsageUseCase tests)
- [x] Commit `b533a0e` exists (AgentChatUseCase tests + docs)
- [x] `pytest tests/application/` — 18 passed
- [x] GetMonthlyUsageUseCase: 7 tests (≥4 required)
- [x] AgentChatUseCase: 11 tests (≥5 required)
- [x] Zero real DB or HTTP calls in any test
