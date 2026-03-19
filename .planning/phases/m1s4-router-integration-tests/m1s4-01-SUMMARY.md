---
phase: m1s4-router-integration-tests
plan: 01
subsystem: testing
tags: [pytest, fastapi, testclient, integration, httpx, dependency-overrides, mocking]

requires:
  - phase: m1s3-use-case-tests
    provides: MockApplicationContainer in conftest.py, asyncio_mode=auto, 18 passing use case tests

provides:
  - 23 passing integration tests (8 health + 15 auth)
  - TestClient fixture pattern with lifespan patching established for all future integration tests
  - pwd_context.hash/verify bypass for passlib+bcrypt version incompatibility
  - docs/learning/pytest_fastapi.md "Integration testing FastAPI with TestClient" section

affects:
  - any future router integration tests (reuse client fixture pattern)
  - m1s5 and beyond (full test suite now has domain + use case + integration layers)

tech-stack:
  added: []
  patterns:
    - "lifespan patch: patch initialize_container + shutdown_container before TestClient starts"
    - "dependency_overrides: override get_container on app to inject MockApplicationContainer"
    - "async context manager mock: asynccontextmanager + AsyncMock session for DB-touching routers"
    - "pwd_context patch: bypass passlib+bcrypt incompatibility by patching hash/verify in router module"

key-files:
  created:
    - tests/integration/__init__.py
    - tests/integration/test_health.py
    - tests/integration/test_auth.py
  modified:
    - docs/learning/pytest_fastapi.md

key-decisions:
  - "Health endpoint is at /health/ not /health — router uses redirect_slashes=False at both router and app level"
  - "passlib+bcrypt version incompatibility (bcrypt lacks __about__) requires patching pwd_context.hash/verify at the router module level — documented as deviation Rule 2 (auth correctness)"
  - "Auth register/login use dict payloads (not Pydantic), so invalid fields return 400 not 422 — test suite reflects actual router behaviour"
  - "Lifespan patching strategy chosen over test-only app factory — keeps tests tied to the real create_application() call path"

requirements-completed: []

duration: 10min
completed: 2026-03-19
---

# Phase m1s4 Plan 01: Router Integration Tests Summary

**23 TestClient integration tests covering /health/ (8 tests) and /v1/api/auth/* (15 tests) with full lifespan + dependency patching, mocked DB sessions, and a pwd_context bypass for the passlib/bcrypt version incompatibility**

## Performance

- **Duration:** ~10 min
- **Started:** 2026-03-19T09:43:13Z
- **Completed:** 2026-03-19T09:53:32Z
- **Tasks:** 3
- **Files modified:** 4 (2 created test files, 1 __init__.py, 1 docs update)

## Accomplishments

- 8 health endpoint tests: GET /health/ returns 200, has `status`, `timestamp`, `version`, accessible without auth; GET /health/live returns 200 with `alive: true`
- 15 auth endpoint tests: register success/existing user/400 for missing fields/expires_in; login success/401 wrong password/401 unknown user/400 missing fields/user echo/token format; refresh valid token/401 invalid token
- Container mock injected via `app.dependency_overrides[get_container]` — cleanest injection point
- Lifespan patched via `patch("main.initialize_container")` so TestClient never touches real infra
- `docs/learning/pytest_fastapi.md` extended with "Integration testing FastAPI with TestClient" section (~100 lines)

## Task Commits

1. **Task 1: Health endpoint tests** — `2b5fed7` (feat)
2. **Task 2: Auth endpoint integration tests** — `35b1cd9` (feat)
3. **Task 3: Learning doc TestClient section** — `72f3787` (docs)

## Files Created/Modified

- `tests/integration/__init__.py` — package marker (empty)
- `tests/integration/test_health.py` — 8 tests: /health/ and /health/live
- `tests/integration/test_auth.py` — 15 tests: register, login, refresh
- `docs/learning/pytest_fastapi.md` — appended ~100-line TestClient section

## Coverage Results

| Layer | Notes |
|---|---|
| `src/presentation/api/routers/auth.py` | Register + login + refresh paths covered by integration tests |
| `src/presentation/api/routers/health.py` | Basic + liveness paths covered |
| Overall `src/` | 41% — integration layer now adds coverage on top of domain + use case tests |

## Decisions Made

- Health endpoint is at `/health/` (trailing slash) because the router uses `@router.get("/")` with `redirect_slashes=False` on both router and app — the combined path is `/health/`. Tests call the exact path rather than relying on redirect.
- passlib+bcrypt version incompatibility (`module 'bcrypt' has no attribute '__about__'`) discovered during auth test execution. Worked around by patching `pwd_context.hash` and `pwd_context.verify` in the `auth` router module namespace. The incompatibility is a pre-existing environment issue (bcrypt library too new for the installed passlib version).
- Auth router validates email/password manually (not via Pydantic), so missing fields return HTTP 400, not 422. Tests assert 400 to match actual behaviour.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Health endpoint path is /health/ not /health**
- **Found during:** Task 1 (first test run returned 404)
- **Issue:** Plan examples used `/health`, but router has `@router.get("/")` with `redirect_slashes=False` — actual path is `/health/`
- **Fix:** Updated all health test calls to use `/health/`
- **Files modified:** `tests/integration/test_health.py`
- **Commit:** `2b5fed7`

**2. [Rule 2 - Missing Critical Functionality] passlib/bcrypt incompatibility breaks all hashing**
- **Found during:** Task 2 (first auth test run returned 500 with ValueError: password cannot be longer than 72 bytes)
- **Issue:** The installed `bcrypt` library version is newer than `passlib` expects — `_bcrypt.__about__` is missing. `pwd_context.hash()` raises `ValueError` inside `detect_wrap_bug()` regardless of password length. This is a security-critical function (it means the production app cannot hash passwords either).
- **Fix:** Patched `src.presentation.api.routers.auth.pwd_context.hash` and `.verify` in test fixtures. Production code not changed — this is an environment issue, logged as deferred item.
- **Files modified:** `tests/integration/test_auth.py`
- **Commit:** `35b1cd9`

### Deferred Items

- `passlib` + `bcrypt` version incompatibility should be resolved in production dependencies: either downgrade `bcrypt` to `<4.0` or upgrade to a `passlib` fork that supports modern bcrypt. Logged to `deferred-items.md`.

## Self-Check

- [x] `tests/integration/__init__.py` exists
- [x] `tests/integration/test_health.py` exists (28 lines min — actual: 128 lines)
- [x] `tests/integration/test_auth.py` exists (60 lines min — actual: 340 lines)
- [x] `docs/learning/pytest_fastapi.md` has TestClient section
- [x] Commit `2b5fed7` exists (health tests)
- [x] Commit `35b1cd9` exists (auth tests)
- [x] Commit `72f3787` exists (docs)
- [x] `pytest tests/integration/` — 23 passed
- [x] `pytest tests/` — 258 passed, 3 xfailed
- [x] GET /health/ returns 200 without auth
- [x] POST /v1/api/auth/register returns 200 for valid data, 400 for missing fields
- [x] POST /v1/api/auth/login returns access_token on success, 401 for wrong password
