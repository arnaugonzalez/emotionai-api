# Testing Patterns

**Analysis Date:** 2026-03-19

## Test Framework

**Runner:**
- pytest 7.4.0+ (from `requirements.txt`: `pytest>=7.4.0`)
- pytest-asyncio 0.21.0+ for async test support (from `requirements.txt`: `pytest-asyncio>=0.21.0`)
- Config: No explicit `pytest.ini` or `pyproject.toml [tool.pytest.*]` found — uses pytest defaults

**Assertion Library:**
- Python's built-in `assert` statements
- No Pydantic validators for test data validation (yet)

**Run Commands:**
```bash
pytest tests/                  # Run all tests in tests/ directory
pytest tests/ -v               # Verbose output
pytest tests/ -k "test_name"   # Run tests matching pattern
pytest tests/ --tb=short       # Short traceback format
pytest tests/ -x               # Stop on first failure
pytest tests/ --asyncio-mode=auto  # Auto asyncio mode for pytest-asyncio
```

## Test File Organization

**Location:**
- Co-located structure: `tests/` directory mirrors `src/` structure
- `tests/domain/` — domain layer tests
- `tests/application/` — application layer tests
- `tests/infrastructure/` — (currently empty, should contain integration tests)

**Naming:**
No explicit `test_*.py` pattern enforced in current tests, but should follow:
- Test files: `test_*.py` or `*_test.py` (pytest auto-discovery)
- Test functions: `def test_*()` or `async def test_*()`
- Fixture files: `conftest.py` (currently missing from project root and test subdirectories)

**Current Structure:**
```
tests/
├── application/
│   ├── chat/
│   │   └── use_cases/
│   │       └── (empty - test_agent_chat_use_case.py was deleted)
│   ├── dtos/
│   │   └── (empty - test_chat_dtos.py, test_profile_dtos.py were deleted)
│   ├── usage/
│   │   └── use_cases/
│   │       └── (empty - test_get_monthly_usage_use_case.py was deleted)
│   ├── (empty - test_exceptions.py was deleted)
├── domain/
│   ├── chat/
│   │   └── (empty - test_entities.py was deleted)
│   ├── entities/
│   │   └── (empty - test_user.py was deleted)
│   ├── events/
│   │   └── (empty - test_domain_events.py was deleted)
│   └── value_objects/
│       └── (empty - test_agent_personality.py, test_user_profile.py were deleted)
└── (conftest.py missing)
```

## Test Structure

**Current State:**
Test files exist in `.pytest_cache/` but source files have been removed from the repository. This indicates a recent cleanup or removal of existing tests.

**Cached test names indicate prior patterns:**
- `test_agent_chat_use_case.py` (under `tests/application/chat/use_cases/`)
- `test_chat_dtos.py`, `test_profile_dtos.py` (under `tests/application/dtos/`)
- `test_get_monthly_usage_use_case.py` (under `tests/application/usage/use_cases/`)
- `test_exceptions.py` (under `tests/application/`)
- `test_entities.py` (under `tests/domain/chat/`)
- `test_user.py` (under `tests/domain/entities/`)
- `test_domain_events.py` (under `tests/domain/events/`)
- `test_agent_personality.py`, `test_user_profile.py` (under `tests/domain/value_objects/`)

**Patterns to adopt (Milestone 1 goal):**

Use pytest with async support. Standard test structure:

```python
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_use_case_executes_successfully():
    # Arrange
    user_id = uuid4()
    mock_repository = AsyncMock()
    mock_service = AsyncMock()
    use_case = AgentChatUseCase(
        user_repository=mock_repository,
        agent_service=mock_service,
        # ... other dependencies
    )

    # Act
    result = await use_case.execute(user_id, "therapy", "Hello")

    # Assert
    assert result is not None
    assert result.agent_type == "therapy"
    mock_service.send_message.assert_called_once()
```

## Mocking

**Framework:** `unittest.mock` (standard library)
- `AsyncMock` for async methods
- `MagicMock` for sync methods
- `patch` for module-level mocking

**Patterns for AsyncMock:**

```python
from unittest.mock import AsyncMock

# Mock async method
mock_service = AsyncMock()
mock_service.send_message.return_value = ChatResponse(...)
await mock_service.send_message(user_id, "therapy", "message")

# Mock called assertion
mock_service.send_message.assert_called_once_with(user_id, "therapy", "message")
```

**What to Mock:**
- External services: `IAgentService`, `ITaggingService`, `IEventBus`, LLM APIs
- Database repositories: `IUserRepository`, `IEmotionalRecordRepository`, `IEventRepository`
- External APIs: OpenAI, Anthropic LLM calls (expensive and slow)

**What NOT to Mock:**
- Domain entities: `User`, `UserProfile`, `AgentPersonality` — test the actual business logic
- Value objects: Test immutability and validation directly
- DTOs: Test serialization/deserialization with real instances
- Dataclass conversions: Test mapping functions directly

**Example: Unit test for domain entity**

```python
@pytest.mark.asyncio
async def test_user_can_update_profile():
    # No mocks — test domain logic directly
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hash",
        is_active=True,
    )

    user.update_profile({"name": "John", "age": 30})

    assert user.profile.name == "John"
    assert user.profile.age == 30
    assert len(user.get_domain_events()) > 0  # UserProfileUpdatedEvent
```

## Fixtures and Factories

**Test Data:**
No factory pattern detected in current codebase. For Milestone 1, create:

```python
# tests/conftest.py
import pytest
from uuid import uuid4

@pytest.fixture
def user_id():
    return uuid4()

@pytest.fixture
def mock_user():
    from src.domain.entities.user import User
    return User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
    )

@pytest.fixture
def mock_chat_response():
    from src.application.dtos.chat_dtos import ChatResponse
    return ChatResponse(
        message="Test response",
        agent_type="therapy",
        user_message="Test message",
        conversation_id="conv-123",
    )
```

**Location:**
- Root conftest: `tests/conftest.py` — shared fixtures
- Layer-specific conftest: `tests/{domain|application|infrastructure}/conftest.py` — layer-specific fixtures

**Convention:**
Use `mock_` prefix for fixtures providing mock objects, not `user_`, which should be real/minimal valid instances.

## Coverage

**Requirements:** Not enforced yet. Milestone 1 goal: **>70% on domain and application layers**.

**Target coverage breakdown:**
- Domain layer (entities, value objects, events): **100%** — no external dependencies, fast to test
- Application layer (use cases, DTOs, service interfaces): **80%+** — core business logic
- Infrastructure layer (repositories, services): **50%+** — integration tests preferred, slower feedback
- Presentation layer (routers): **<50%** — rely on integration tests for API coverage

**View Coverage:**
```bash
pytest tests/ --cov=src --cov-report=html
# Opens htmlcov/index.html with line-by-line coverage
```

**Coverage thresholds for CI/CD (future):**
```ini
[coverage:run]
branch = True
omit =
    */tests/*
    */venv/*

[coverage:report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == .__main__.:
min_version = 3.11
fail_under = 70
```

## Test Types

**Unit Tests:**
- Scope: Single class/function in isolation
- Mocking: All external dependencies (services, repositories)
- Speed: <100ms per test
- Location: `tests/domain/`, `tests/application/`
- Examples:
  - Test a domain entity method with no side effects
  - Test a DTO's `__post_init__` validation
  - Test a use case with all dependencies mocked

**Integration Tests:**
- Scope: Use case + real database + real services (or test doubles)
- Mocking: Only external APIs (OpenAI, Anthropic)
- Speed: 1-5 seconds per test
- Location: `tests/infrastructure/` (currently empty — needs creation)
- Examples:
  - Test `AgentChatUseCase` with real SQLAlchemy repository + mocked OpenAI
  - Test event repository and event bus together
  - Test user registration through all layers

**E2E Tests:**
- Not in current test suite
- Would require full API startup, live database, mocked LLMs
- Reserved for smoke tests in deployment pipeline

## Common Patterns

**Async Testing:**

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    # pytest-asyncio automatically handles event loop
    result = await some_async_function()
    assert result is not None
```

**Multiple async calls:**

```python
@pytest.mark.asyncio
async def test_multiple_async_calls():
    # Sequential
    result1 = await service.method1()
    result2 = await service.method2(result1)
    assert result2 is not None

    # Parallel
    import asyncio
    result1, result2 = await asyncio.gather(
        service.method1(),
        service.method2(),
    )
```

**Error Testing:**

```python
import pytest
from src.application.exceptions import ValidationException

@pytest.mark.asyncio
async def test_validates_input():
    use_case = AgentChatUseCase(...)

    with pytest.raises(ValidationException) as exc_info:
        await use_case.execute(user_id, "", "message")  # Empty agent_type

    assert "agent_type" in str(exc_info.value)
```

**DTO validation:**

```python
import pytest
from src.application.dtos.chat_dtos import ChatRequest

def test_chat_request_validates_message_length():
    with pytest.raises(ValueError, match="Message too long"):
        ChatRequest(
            user_id=uuid4(),
            message="x" * 2001,  # > 2000 chars
            agent_type="therapy",
        )

def test_chat_request_validates_agent_type():
    with pytest.raises(ValueError, match="Invalid agent type"):
        ChatRequest(
            user_id=uuid4(),
            message="Hello",
            agent_type="invalid",  # Not in ["therapy", "wellness"]
        )
```

**Repository testing pattern:**

```python
@pytest.mark.asyncio
async def test_user_repository_saves_and_retrieves():
    db_connection = # ... real test database
    repo = SqlAlchemyUserRepository(db_connection)

    # Arrange
    user = User(id=uuid4(), email="test@example.com", ...)

    # Act
    await repo.save(user)
    retrieved = await repo.get_by_id(user.id)

    # Assert
    assert retrieved is not None
    assert retrieved.email == user.email
```

## Test Execution

**Quick feedback loop (5-30 seconds):**
```bash
pytest tests/domain/ tests/application/dtos tests/application/exceptions -v --tb=short
```

**Full unit test suite (30 seconds - 2 minutes, once written):**
```bash
pytest tests/ -v --tb=short
```

**With coverage report:**
```bash
pytest tests/ --cov=src.domain --cov=src.application --cov-report=term-missing
```

**Watch mode (needs pytest-watch):**
```bash
ptw -- tests/domain/ -v
```

## Current Test Debt

**P0 — Blocks Milestone 1:**
1. No conftest.py with shared fixtures
2. Test files deleted from repository (seen in `.pytest_cache/` but sources removed)
3. No unit test suite for use cases (`AgentChatUseCase`, `GetMonthlyUsageUseCase` are critical)
4. No domain entity unit tests (`User`, `UserProfile` validation)
5. No DTO validation tests

**P1 — Test Coverage Gaps:**
- `src/presentation/api/routers/` — no unit tests (mock container, services)
- `src/infrastructure/services/` — no unit tests for LLM/tagging services
- `src/infrastructure/repositories/` — no integration tests with test database
- Middleware (`error_handling.py`, `logging.py`, `rate_limiting.py`) — untested
- Exception handling paths — not validated

**P2 — Infrastructure for Milestone 1:**
- Create `tests/conftest.py` with base fixtures
- Set up pytest asyncio mode in pyproject.toml or pytest.ini
- Configure coverage reporting
- Add conftest to `tests/domain/` and `tests/application/` for layer-specific fixtures
- Create test database fixture for integration tests

## Milestone 1 Goals

**Target: >70% coverage on domain + application layers**

**Deliverables:**
1. Unit tests for all domain entities and value objects (`tests/domain/`)
2. Unit tests for all use cases (`tests/application/chat/use_cases/`, `tests/application/usage/use_cases/`)
3. DTO validation tests (`tests/application/dtos/`)
4. Service interface compliance tests (`tests/application/services/`)
5. Conftest setup with async fixtures and mocking patterns
6. Coverage report showing >70% on domain and application

**Not in scope:**
- Presentation layer tests (routers/middleware)
- Infrastructure integration tests with real databases
- E2E tests

---

*Testing analysis: 2026-03-19*
