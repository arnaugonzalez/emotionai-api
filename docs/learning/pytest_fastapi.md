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

## Further reading

- [pytest-asyncio docs](https://pytest-asyncio.readthedocs.io/)
- [SQLAlchemy 2.0 async docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [unittest.mock AsyncMock](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)
