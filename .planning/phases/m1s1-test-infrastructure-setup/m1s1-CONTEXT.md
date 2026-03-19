# Milestone 1, Slice 1.1: Test Infrastructure Setup — Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Set up the pytest foundation so all subsequent test slices (1.2–1.4) have a consistent infrastructure to build on.

Deliverables:
- `pyproject.toml` with `[tool.pytest.ini_options]` and `[tool.coverage.run]` config
- `tests/conftest.py` with async engine fixture (SQLite in-memory), mock ApplicationContainer factory, mock repository base class
- `pytest -q` passes (0 tests, no errors)
- `docs/learning/pytest_fastapi.md` — stub covering what's set up in this slice

Writing tests for domain entities, use cases, or routers is **out of scope** for this slice — that's Slices 1.2–1.4.

</domain>

<decisions>
## Implementation Decisions

### Coverage configuration
- `source = ["src"]` — track full src/ directory
- `branch = true` — branch coverage enabled from the start
- `omit = ["migrations/*", "tests/*", "**/__pycache__/*"]`
- **No `fail_under` threshold yet** — add after Slice 1.2 when domain tests exist. Setting it now would cause immediate failure with 0% coverage.

### Learning doc: pytest_fastapi.md
- **Audience**: Personal study guide (future self) — personal voice, "here's what clicked for me"
- **Scope now**: Cover only what Slice 1.1 sets up — pytest-asyncio config, asyncio_mode=auto, and coverage setup
- **Grow with slices**: Add TestClient section in Slice 1.4, mocking patterns in Slice 1.3 — when those patterns are actually implemented
- **Code examples**: Use real project code (GetMonthlyUsageUseCase, User entity) — not generic examples

### Existing test state
- `tests/` directory exists with correct subfolder structure (domain/, application/)
- All source `.py` test files have been deleted — only `.pyc` cache artifacts remain
- No `conftest.py`, no `pyproject.toml`, no `pytest.ini` — clean slate
- The `.pyc` names reveal what was previously tested: agent_chat_use_case, get_monthly_usage_use_case, chat/entities, user entity, value_objects, DTOs — useful reference for Slices 1.2–1.3

### Claude's Discretion
- Exact structure of the mock ApplicationContainer factory (what interfaces to expose)
- Mock repository base class design (abstract class vs Protocol vs concrete AsyncMock wrapper)
- Whether to use `aiosqlite` driver for the SQLite async engine fixture, or skip the DB fixture if not needed at this slice
- `asyncio_mode = auto` in pytest config (already specified in roadmap — no decision needed)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/infrastructure/container.py` — `ApplicationContainer` is the real DI root; mock factory should mirror its interface (repositories + services)
- `src/domain/entities/user.py`, `src/application/use_cases/` — available for code examples in learning doc
- `requirements.txt` — `pytest>=7.4.0`, `pytest-asyncio>=0.21.0`, `httpx>=0.25.0` already present; `aiosqlite` NOT present (needed for async SQLite fixture)

### Established Patterns
- No existing conftest.py or pyproject.toml — completely fresh, no patterns to conflict with
- `src/infrastructure/container.py` uses a handwritten DI pattern (not dependency-injector library, which is unused and should be removed per CONCERNS.md)

### Integration Points
- `tests/` directory structure mirrors `src/` — `tests/domain/`, `tests/application/`, `tests/infrastructure/`
- conftest.py at `tests/conftest.py` (root) provides shared fixtures; layer-specific conftest files can live in subdirectories

</code_context>

<specifics>
## Specific Ideas

- The `.pyc` artifacts reveal the intended test file names — useful when Slices 1.2–1.3 write those tests: `test_agent_chat_use_case.py`, `test_get_monthly_usage_use_case.py`, `test_user.py`, `test_domain_events.py`, `test_agent_personality.py`, `test_user_profile.py`, `test_chat_dtos.py`, `test_profile_dtos.py`, `test_exceptions.py`, `test_entities.py`
- learning doc voice: personal, "this is how I think about pytest-asyncio in this project", not a textbook entry

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: m1s1-test-infrastructure-setup*
*Context gathered: 2026-03-19*
