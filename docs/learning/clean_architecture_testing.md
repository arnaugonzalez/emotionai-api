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
