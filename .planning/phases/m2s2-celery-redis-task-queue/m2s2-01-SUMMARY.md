---
phase: m2s2-celery-redis-task-queue
plan: 01
subsystem: infra
tags: [celery, redis, flower, docker-compose, testing]
requires:
  - phase: m2s1.1-demo-flow-hardening
    provides: step-based demo flow and current observability docker-compose baseline
provides:
  - standalone Celery app under src.infrastructure.tasks
  - notify_new_record shared task stub with retry/backoff
  - celery_worker and flower docker-compose services
  - task body unit tests runnable without Redis
affects: [m2s2-02, m2s2-03, docs/learning/celery_redis.md]
tech-stack:
  added: [celery, flower]
  patterns: [standalone worker module, shared_task lazy registration, direct task-body unit tests]
key-files:
  created:
    - src/infrastructure/tasks/__init__.py
    - src/infrastructure/tasks/worker.py
    - src/infrastructure/tasks/notification_tasks.py
    - tests/infrastructure/__init__.py
    - tests/infrastructure/tasks/__init__.py
    - tests/infrastructure/tasks/test_notification_tasks.py
  modified:
    - requirements.txt
    - requirements-production.txt
    - docker-compose.yml
key-decisions:
  - "worker.py reads REDIS_URL directly from os.environ and imports no container/app modules so Celery workers stay decoupled from FastAPI startup."
  - "notification_tasks.py uses @shared_task instead of binding directly to celery_app so task modules remain lazily registrable."
  - "Task verification uses .venv/bin/python because the environment has no python shim on PATH."
patterns-established:
  - "Celery worker modules in this repo must be import-safe and must not transitively boot the FastAPI application."
  - "Task logic is unit-tested through Task.run(...) so broker-free assertions cover task bodies before dispatch integration is added."
requirements-completed: [m2s2-01]
duration: 20min
completed: 2026-03-19
---

# Phase m2s2 Plan 01: Celery task queue foundation Summary

**Standalone Celery worker app with Redis-backed task stubs, local Flower monitoring, and broker-free unit tests for notification task bodies**

## Performance

- **Duration:** 20 min
- **Started:** 2026-03-19T14:21:13Z
- **Completed:** 2026-03-19T14:41:13Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments
- Added `src/infrastructure/tasks/` as an isolated package that Celery can import without booting FastAPI or the DI container.
- Added `notify_new_record` as a shared Celery task stub with retry, backoff, jitter, and deterministic response payload.
- Added Celery/Flower dependencies, local docker-compose services, and focused task-body tests under `tests/infrastructure/tasks/`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create src/infrastructure/tasks/ package** - `e02c640` (feat)
2. **Task 2: Add Celery + Flower to requirements and docker-compose** - `41a28be` (chore)
3. **Task 3: Create test scaffold for tasks package** - `131f0c7` (test)

## Files Created/Modified
- `src/infrastructure/tasks/__init__.py` - Package marker for the new Celery task namespace.
- `src/infrastructure/tasks/worker.py` - Standalone Celery app singleton reading `REDIS_URL` from the environment only.
- `src/infrastructure/tasks/notification_tasks.py` - Shared `notify_new_record` task stub with retry/backoff config and structured return payload.
- `requirements.txt` - Added Celery Redis transport and Flower for local/dev environments.
- `requirements-production.txt` - Added Celery Redis transport and Flower for production dependency parity.
- `docker-compose.yml` - Added `celery_worker` and `flower` services while preserving existing db/redis/api/prometheus/grafana services.
- `tests/infrastructure/tasks/test_notification_tasks.py` - Added direct `.run()` unit coverage for the notification task body.

## Decisions Made
- Kept `worker.py` completely independent of `container.py`, routers, and app startup to avoid Celery worker circular boot side effects.
- Used `@shared_task` in `notification_tasks.py` so task registration remains lazy via the worker `include` list.
- Verified via `.venv/bin/python` because the local environment does not expose a `python` executable on PATH.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Initial task verification with `python` failed because only `.venv/bin/python` / `python3` are available in this environment. Verification was rerun against the project venv.
- Task 1 verification initially failed because `celery` was not installed in `.venv`; installed the newly declared dependencies to verify the updated slice in the project interpreter.
- The Task 3 TDD slice could not produce a meaningful RED phase because the task implementation was already present from Task 1; tests passed on first execution and were captured in a single test commit instead of a forced failing-test commit.
- Full-suite verification still fails only on the three pre-existing strict `XPASS` domain tests in `tests/domain/test_user.py`, matching the blocker already documented in `STATE.md`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Ready for plan `m2s2-02` to wire Celery into the container and dispatch background work from the records flow.
- The worker import contract is now established: future task modules should remain standalone and broker-safe.

## Self-Check: PASSED
- FOUND: `.planning/phases/m2s2-celery-redis-task-queue/m2s2-01-SUMMARY.md`
- FOUND: `e02c640`
- FOUND: `41a28be`
- FOUND: `131f0c7`

---
*Phase: m2s2-celery-redis-task-queue*
*Completed: 2026-03-19*
