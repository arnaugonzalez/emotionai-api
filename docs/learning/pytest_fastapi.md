# pytest + FastAPI — EmotionAI study guide

## What is it and why do we use it here

pytest is Python's de-facto test runner. It finds functions named `test_*`, runs
them, and reports failures with clear diffs. The `pytest-asyncio` plugin extends it
to support `async def test_*` functions — which is what we need here.

EmotionAI is fully async: every database call uses `asyncpg` or `aiosqlite`, the
LangChain agent is async, and FastAPI route handlers are all `async def`. A
synchronous test runner cannot `await` coroutines, so without `pytest-asyncio`
every async test would silently pass (the coroutine object is truthy!) without
ever actually running. That's the kind of bug that haunts you.

---

## How it works conceptually

### asyncio_mode = "auto"

Without this setting you have to decorate every async test:

```python
# Old way — verbose
@pytest.mark.asyncio
async def test_something():
    result = await some_coroutine()
    assert result == 42
```

With `asyncio_mode = "auto"` in pyproject.toml, pytest-asyncio wraps all `async def`
test functions automatically. No decorator needed. I set this because every test in
EmotionAI is async (repositories, use cases, route handlers — all async).

### The fixture system

pytest's fixture system is dependency injection for tests. A fixture is a function
decorated with `@pytest.fixture`. When a test declares a parameter with the same
name as a fixture, pytest injects the fixture's return value.

```python
@pytest.fixture()
def mock_container():
    return MockApplicationContainer()

async def test_something(mock_container):
    # mock_container is injected automatically
    mock_container.user_repository.get_by_id.return_value = ...
```

Fixtures compose: a fixture can itself declare other fixtures as parameters. The
scope (`"function"`, `"session"`) controls how often the fixture runs.

### conftest.py as the shared fixture home

pytest automatically discovers and loads `conftest.py` files. Fixtures defined in
`tests/conftest.py` are available to every test in the `tests/` tree without any
import statement. This is where shared infrastructure lives.

---

## Key patterns used in this project (slice 1.1 setup)

### pyproject.toml config (annotated)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]        # only look here — don't scan src/ or migrations/
asyncio_mode = "auto"        # no @pytest.mark.asyncio needed on async tests
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.coverage.run]
source = ["src"]             # measure coverage in src/ only
branch = true                # count branch coverage, not just line coverage
omit = [
    "migrations/*",          # generated Alembic files — not ours to test
    "tests/*",               # test files don't count toward coverage
    "**/__pycache__/*",
    "src/infrastructure/config/settings.py",  # just Pydantic field declarations
]

[tool.coverage.report]
show_missing = true          # show which lines aren't covered
skip_covered = false         # always show all files
# NOTE: no fail_under yet — coverage starts at 0 until slice 1.2 ships tests
```

### MockApplicationContainer fixture — why we mock the container, not the DB

The real `ApplicationContainer` from `src/infrastructure/container.py` connects to
PostgreSQL, Redis, and OpenAI on startup. We can't do that in unit tests.

The naive fix is to spin up a test database. But then tests are slow, non-deterministic
(state leaks between tests), and fail when Postgres isn't running. Been there.

The better approach: mock the container. Every router and use case receives the
container as a dependency. In tests, inject a `MockApplicationContainer` instead.
Now tests run in milliseconds with no external services.

```python
# From tests/conftest.py
class MockApplicationContainer:
    """Mirrors the @dataclass attributes from src/infrastructure/container.py."""

    def __init__(self) -> None:
        # Each service is an AsyncMock — awaitable and inspectable
        self.user_repository = AsyncMock()
        self.agent_chat_use_case = AsyncMock()
        self.get_monthly_usage_use_case = AsyncMock()
        # ... all other attributes from ApplicationContainer ...

@pytest.fixture()
def mock_container() -> MockApplicationContainer:
    return MockApplicationContainer()
```

The attribute names must match exactly — I read `container.py` and copied them.
That's the "mirror" contract: if `ApplicationContainer` adds a new service,
`MockApplicationContainer` needs updating too.

### async_engine fixture — SQLite for integration tests

Some tests need a real database layer (not mocks). For those, we use an in-memory
SQLite engine via `aiosqlite`:

```python
@pytest.fixture(scope="session")
async def async_engine() -> AsyncEngine:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.drop_all)
    await engine.dispose()
```

One subtlety: production models in `src/infrastructure/database/models.py` use
PostgreSQL-specific types (`UUID`, `JSONB`). SQLite doesn't support these. So the
`async_engine` fixture uses a separate `TestBase` with SQLite-compatible schema
definitions, which live alongside the tests that need them.

---

## What's coming in later slices

- **Slice 1.2 (domain tests):** Pure unit tests for `User`, `AgentPersonality`,
  `UserProfile` — no fixtures needed, just instantiation and assertions.
- **Slice 1.3 (use case tests):** `mock_container` fixture used to test
  `AgentChatUseCase` and `GetMonthlyUsageUseCase` in isolation.
- **Slice 1.4 (router integration tests):** `TestClient` from `httpx` + FastAPI's
  `override_dependency` pattern to test the HTTP layer with mocked use cases.

---

## Common mistakes and how to avoid them

**asyncio_mode not set** — symptom: tests pass instantly but nothing actually ran.
Coroutines are truthy objects. Without `asyncio_mode = "auto"`, an `async def` test
is collected and "passes" without ever being awaited. Always check
`pytest --co -v` to see what's collected.

**Mocking at the wrong layer** — mocking the database directly (e.g., patching
`asyncpg.connect`) instead of the service interface means your tests are testing the
mock, not the code. Mock at the boundary defined by the application layer interfaces:
`IUserRepository`, `IAgentService`, etc.

**Using the real container in tests** — if you import `ApplicationContainer` and call
`ApplicationContainer.create()` in a test, pytest will try to connect to PostgreSQL,
Redis, and OpenAI. Tests will fail or hang in CI. Always use `mock_container`.

**Session-scoped fixtures that mutate state** — the `async_engine` is session-scoped
for speed. Don't mutate shared database state in tests that use it; use transactions
that roll back, or use function-scoped db fixtures in those tests.

---

## Integration testing FastAPI with TestClient

### What is TestClient

FastAPI ships with a `TestClient` backed by `httpx`. It lets you make
synchronous HTTP requests to your FastAPI app in tests — no running server
needed. The app is called directly in-process, so you get real routing, real
middleware, and real exception handlers — just without real infrastructure.

```python
from fastapi.testclient import TestClient
from main import create_application

app = create_application()
with TestClient(app) as client:
    response = client.get("/health/")
    assert response.status_code == 200
```

### The lifespan problem

EmotionAI's `create_application()` attaches a `lifespan` context manager that
calls `initialize_container()` on startup. That function connects to PostgreSQL,
Redis, and (optionally) OpenAI. When TestClient enters its context manager
(`with TestClient(app) as c`), it fires the lifespan — meaning tests would
hang or fail trying to reach real infrastructure.

Fix: patch `initialize_container` and `shutdown_container` before the TestClient
starts. Return a `MockApplicationContainer` from the patched `initialize_container`
so that `app.state.container` is populated (the lifespan stores it there).

### The container injection problem

Routers get their dependencies via `get_container` from `deps.py`:

```python
def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container
```

Two options to inject a mock:

**Option A — dependency_overrides (preferred):** Override `get_container`
directly on the FastAPI app object. Clean, explicit, and works independently
of how the container ends up in app.state.

```python
app.dependency_overrides[get_container] = lambda: mock_container
```

**Option B — app.state injection:** Set `app.state.container = mock_container`
before the TestClient starts. Simpler, but silently breaks if a router ever
bypasses `get_container` and reads `request.app.state.container` directly.

In EmotionAI we use both: the lifespan patch supplies `mock_container` to
`app.state`, and `dependency_overrides` explicitly wires it to `get_container`.

### Pattern used in this project

```python
@pytest.fixture()
def client():
    mock_container = MockApplicationContainer()

    with (
        patch("main.initialize_container", new=AsyncMock(return_value=mock_container)),
        patch("main.shutdown_container", new=AsyncMock()),
    ):
        from main import create_application
        from src.presentation.api.routers.deps import get_container

        app = create_application()
        app.dependency_overrides[get_container] = lambda: mock_container

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c, mock_container

        app.dependency_overrides.clear()
```

`raise_server_exceptions=True` is the default and ensures that unhandled
server-side exceptions propagate into the test (useful for debugging).

### Mocking a DB session inside a router

Auth.py calls `container.database.get_session()` as an async context manager:

```python
async with db.get_session() as session:
    ...
```

In tests, set `container.database.get_session` to a function that returns an
async context manager yielding a mock session:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def _get_session():
    mock_session = AsyncMock()
    mock_session.execute.return_value = some_result_mock
    yield mock_session

container.database.get_session = _get_session
```

### Patching third-party code called inside routers

If a router calls a library function directly (e.g. `pwd_context.hash()`),
mock it via `patch()` targeting the router module's namespace — not the library:

```python
patch("src.presentation.api.routers.auth.pwd_context.hash", side_effect=lambda s: "fake_hash")
```

This is important in EmotionAI where `passlib` + `bcrypt` have a version
incompatibility (`module 'bcrypt' has no attribute '__about__'`). The auth
tests patch both `hash` and `verify` so tests never call real bcrypt.

### What to test at the integration level

- HTTP status codes for success and error paths (200, 400, 401, 422, 500)
- Response body shape — key fields present (`access_token`, `user`, `status`)
- Request validation — FastAPI returns 422 automatically for Pydantic model
  violations; 400 when routers validate manually
- Auth middleware behaviour — no Authorization header on protected routes → 403

### What NOT to test at integration level

- Business logic (that belongs in use case tests — see clean_architecture_testing.md)
- DB query correctness (that belongs in infrastructure / repository tests)
- Exact values returned by real services — use unit tests for that

---

## Further reading

- [pytest-asyncio docs](https://pytest-asyncio.readthedocs.io/)
- [SQLAlchemy 2.0 async docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [unittest.mock AsyncMock](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)
