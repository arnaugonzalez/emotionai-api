# Clean Architecture Testing — EmotionAI Study Guide

## What Is It and Why Do We Use It Here

Clean Architecture separates code into layers so each one can be built, changed, and tested independently. In EmotionAI the layers are:

```
domain → application → infrastructure → presentation
```

Each arrow means "depends on". Domain depends on nothing. Presentation depends on everything.

The payoff: you can test each layer with exactly the tools it deserves — and nothing more.

- **Domain tests**: pure Python, run in milliseconds, zero mocks
- **Application / use case tests**: mock only the infrastructure boundary
- **Infrastructure tests**: use real databases (SQLite in tests, Postgres in prod)
- **Router integration tests**: TestClient + mock container, no real network

This document covers the domain layer. Later sections will cover use cases, repositories, and routers.

---

## Testing the Domain Layer

### The Key Insight

Domain = pure Python. No FastAPI, no SQLAlchemy, no OpenAI, no HTTP. Tests need zero mocks because there is nothing to mock. You just construct objects and assert facts.

The test file for `User` has 32 tests and imports:

```python
import pytest
from src.domain.entities.user import User
from src.domain.value_objects.agent_personality import AgentPersonality
```

That is the entire dependency list. No fixtures, no patches, no async. It runs in 0.3 seconds.

### Pattern: Construct and Assert

```python
def make_user(**kwargs) -> User:
    defaults = {"email": "alice@example.com", "hashed_password": "hashed_secret"}
    defaults.update(kwargs)
    return User(**defaults)

def test_deactivate_sets_is_active_false():
    user = make_user()
    user.deactivate()
    assert user.is_active is False
```

One function, one behaviour. No setup class, no shared state.

The helper `make_user()` provides a valid default and lets individual tests override specific fields. This keeps each test readable without repeating boilerplate.

### What to Test

**Every constructor with valid data** — verify defaults are sensible, field types are correct, and UUIDs are unique across instances.

**Every business method** — these are the "why" of the entity. `User.deactivate()`, `User.change_agent_personality()`, `AgentPersonality.from_string()`, `UserProfile.is_complete()`. If the method is on the entity, it captures a business rule and deserves a test.

**Edge cases and boundary values** — what happens with an empty list? With `None`? With the same value twice? Example from our tests:

```python
def test_change_agent_personality_same_value_noop():
    """Changing to the same personality should not advance updated_at."""
    user = make_user()
    original_updated = user.updated_at
    user.change_agent_personality(AgentPersonality.EMPATHETIC_SUPPORTIVE)
    assert user.updated_at == original_updated
```

**Exceptions raised for invalid state** — test that `pytest.raises(...)` catches the right exception type.

**Equality and hashing** — if the entity defines `__eq__` and `__hash__`, test that two objects with the same identity are equal and can coexist in a set.

### What NOT to Test

**Persistence** — whether a User saves to the database is infrastructure's job. The domain entity should never touch SQLAlchemy.

**Serialization** — do not test `dict(user)` or JSON output from the entity. That is the DTO layer's responsibility. UserProfile has `to_dict()` because it doubles as a value object that passes through multiple layers — but we test it at the value object level, not via the ORM.

**Framework-specific behaviour** — no FastAPI response codes, no SQLAlchemy session management, no HTTP headers.

### Documenting Known Bugs With xfail

Domain tests sometimes reveal bugs in the entities being tested. The rule: mark broken tests as `xfail(strict=True)` with a precise reason string. Do not delete the test or make it pass by hiding the bug.

Example from our tests — `User.update_profile()` crashes because `UserProfileUpdatedEvent` requires base fields that User does not provide:

```python
@pytest.mark.xfail(
    strict=True,
    reason=(
        "update_profile() raises TypeError because UserProfileUpdatedEvent "
        "requires event_id/occurred_at/event_type positional args that "
        "User.update_profile() does not supply."
    ),
)
def test_update_profile_replaces_profile():
    user = make_user()
    user.update_profile({"name": "Alice", "age": 30, "gender": "female"})
    assert user.profile.name == "Alice"
```

`strict=True` means: if this test starts passing unexpectedly (the bug was fixed), pytest marks it as XPASS and fails the suite — forcing us to remove the xfail marker. This way bugs do not silently get fixed without updating the test.

### Coverage Target

100% on `src/domain/` is achievable because domain has no conditional IO branches. The only exceptions are:

- Abstract method `pass` stubs — excluded via `exclude_lines = ["@(abc\\.)?abstractmethod"]` in pyproject.toml
- Structurally dead branches (e.g., `if not self.id` when `id` is always set by `default_factory`) — two lines, excluded from the total

Current state: **99% coverage** on `src/domain/` with 217 passing tests (plus 3 documented xfail).

---

## Files Written in This Slice

| File | Tests | What It Covers |
|---|---|---|
| `tests/domain/test_user.py` | 32 | User entity: construction, activation, personality, agent prefs, events, equality |
| `tests/domain/value_objects/test_agent_personality.py` | 19 | AgentPersonality enum: values, descriptions, prompts, preferences, from_string |
| `tests/domain/value_objects/test_value_objects.py` | 27 | UserProfile: immutability, completeness, missing fields, goals, from_dict/to_dict |
| `tests/domain/events/test_domain_events.py` | 30 | All 6 event classes: construction, immutability, inheritance |
| `tests/domain/test_exceptions.py` | 50 | All 10 exception classes: message, attributes, inheritance, parametrized catch |
| `tests/domain/chat/test_chat_entities.py` | 25 | Message, Conversation, AgentContext, TherapyResponse |
| `tests/domain/test_interfaces.py` | 34 | All 6 repository interfaces: ABC enforcement, async method contracts |

Next slice: use case tests — where mocks first appear.

---

## Testing Use Cases

### The Key Insight

Use cases = business logic orchestration. They coordinate domain entities and infrastructure interfaces (repositories, services, event buses). The key rule: use cases depend on **interfaces**, not implementations. Tests inject `AsyncMock` for each interface, so you verify the "what and why" without touching a real database or making real HTTP calls.

A use case test runs in milliseconds and never fails due to network timeouts or database schema changes.

### Pattern: Inject AsyncMock, Assert Behaviour

```python
from unittest.mock import AsyncMock
from src.application.usage.use_cases.get_monthly_usage_use_case import GetMonthlyUsageUseCase

async def test_get_monthly_usage_returns_usage_for_valid_user():
    mock_repo = AsyncMock()
    mock_repo.get_monthly_usage.return_value = 4200

    use_case = GetMonthlyUsageUseCase(token_usage_repository=mock_repo)
    result = await use_case.execute(user_id=USER_ID, year=2026, month=3)

    assert result == 4200
    mock_repo.get_monthly_usage.assert_called_once_with(USER_ID, 2026, 3)
```

Three steps: (1) configure the mock to return known data, (2) call execute, (3) assert the result and how the mock was called.

### What to Test

**Happy path** — mock returns valid data, assert correct return value.

**Error paths** — mock raises or returns None. Assert the use case raises the right exception or handles the failure correctly.

```python
async def test_get_monthly_usage_propagates_repository_exception():
    mock_repo = AsyncMock()
    mock_repo.get_monthly_usage.side_effect = RuntimeError("DB connection lost")
    use_case = GetMonthlyUsageUseCase(token_usage_repository=mock_repo)

    with pytest.raises(RuntimeError, match="DB connection lost"):
        await use_case.execute(user_id=USER_ID, year=2026, month=3)
```

**Interaction verification** — assert the right methods were called with the right arguments. This verifies the use case is delegating correctly, not just producing the right output by coincidence.

**Best-effort paths** — use cases often have non-critical side effects (token logging, event publishing, persisting suggestions) that must not abort the primary response if they fail.

```python
async def test_chat_token_logging_failure_does_not_abort_response():
    token_repo = AsyncMock()
    token_repo.log_usage.side_effect = Exception("logging DB down")
    use_case = make_use_case(agent_service=mock_agent, token_usage_repo=token_repo)

    result = await use_case.execute(user_id=USER_ID, agent_type="therapist", message="Hello")
    assert result is response  # response returned despite logging failure
```

### What NOT to Test

**That AsyncMock works** — you do not need to verify that `mock.some_method.return_value` gets returned. Mock the boundary, test your logic.

**Infrastructure concerns** — do not reach into the mock to verify SQL queries or HTTP request bodies. That belongs in infrastructure tests.

**Framework plumbing** — no FastAPI middleware, no SQLAlchemy sessions, no Redis connections in use case tests.

### Helper Pattern: make_use_case()

Use cases with many dependencies benefit from a `make_use_case()` helper that wires all-mocked defaults and accepts overrides:

```python
def make_use_case(**kwargs) -> AgentChatUseCase:
    defaults = dict(
        user_repository=AsyncMock(),
        agent_service=AsyncMock(),
        token_usage_repo=None,
        # ... all other dependencies
    )
    defaults.update(kwargs)
    return AgentChatUseCase(**defaults)
```

Each test then overrides only what matters: `make_use_case(agent_service=my_mock)`. This avoids repeating 10+ mock lines per test.

### Current State

| File | Tests | What It Covers |
|---|---|---|
| `tests/application/usage/use_cases/test_get_monthly_usage_use_case.py` | 7 | Happy path, zero usage, arg forwarding, default date, error propagation |
| `tests/application/chat/use_cases/test_agent_chat_use_case.py` | 11 | Happy path, crisis passthrough, agent failure, token logging, best-effort skips |
