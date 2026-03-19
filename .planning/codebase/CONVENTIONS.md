# Coding Conventions

**Analysis Date:** 2026-03-19

## Naming Patterns

**Files:**
- Snake_case for all files: `agent_chat_use_case.py`, `openai_tagging_service.py`, `sqlalchemy_user_repository.py`
- Routers grouped by domain: `src/presentation/api/routers/{domain}.py`
- Repositories follow pattern: `sqlalchemy_{entity}_{repository}.py` (e.g., `sqlalchemy_user_repository.py`)
- Service implementations: `{provider}_{service_type}_service.py` (e.g., `openai_llm_service.py`, `redis_event_bus.py`)
- Interfaces suffixed with `I`: `IUserRepository`, `IAgentService`, `IEventBus`

**Functions:**
- Snake_case for all functions and methods: `get_by_id()`, `save_event()`, `send_message()`
- Async functions: `async def method_name()` — never synchronous blocking calls
- Private methods prefixed with `_`: `_model_to_entity()`, `_create_jwt()`, `_add_domain_event()`
- Helper functions at module level: `_parse_jwt()`, `_entity_to_model()` — used for mapping and validation
- Boolean getters: `is_complete()`, `has_crisis_support()`, `is_profile_complete()` — plain names without `get_` prefix

**Variables:**
- Camelcase avoided entirely — always snake_case: `user_id`, `agent_type`, `message_count`
- Type hints required on all function parameters and returns
- DTOs use `Optional[]` for optional fields: `Optional[str]`, `Optional[Dict[str, Any]]`
- Instance variables prefixed with `_` for private state: `self._domain_events`, `self._add_domain_event()`
- Collection names always plural: `goals`, `concerns`, `preferred_activities`

**Types:**
- PascalCase for all classes: `User`, `ChatResponse`, `UserProfile`, `AgentPersonality`
- Enum classes use PascalCase: `AgentPersonality`, inherit from `Enum` with `.value` property
- DTO classes suffixed with `Request` or `Response`: `ChatRequest`, `ChatResponse`, `TokenResponse`
- Value objects defined in `value_objects/` directory: `UserProfile`, `AgentPersonality`
- Dataclasses used for immutable structures: `@dataclass(frozen=True)` for DTOs and value objects
- Regular dataclasses: `@dataclass` for entities and mutable structures like `User`

## Code Style

**Formatting:**
- Black-style formatting enforced (from requirements.txt: `black>=23.0.0`, `isort>=5.12.0`)
- Line length follows FastAPI conventions (typically 100-120 chars)
- No explicit style guide file found, but patterns follow PEP 8 strictly

**Linting:**
- No `.flake8`, `ruff.toml`, or `pylintrc` found — relies on implicit PEP 8 conformance
- Code is well-structured with clear separation of concerns
- Docstrings are descriptive module-level comments, not function-level docstrings

**File-level docstrings:**
All files include module-level docstring describing purpose:
```python
"""
Domain Entity: User

This represents the core User business entity with all business logic
encapsulated within the entity itself.
"""
```

## Import Organization

**Order:**
1. Standard library (`logging`, `asyncio`, `datetime`, `dataclasses`, `typing`)
2. Third-party framework imports (`fastapi`, `sqlalchemy`, `pydantic`, `jwt`)
3. Internal domain layer (`from ..domain.entities.user import User`)
4. Internal application layer (`from ...application.services.agent_service import IAgentService`)
5. Internal infrastructure layer (`from ...infrastructure.database.connection import DatabaseConnection`)
6. Internal presentation layer (`from ...presentation.api.routers.deps import get_container`)

**Example from `src/application/chat/use_cases/agent_chat_use_case.py`:**
```python
import logging
from typing import Dict, Any, Optional
from uuid import UUID

from ....domain.users.interfaces import IUserRepository
from ....domain.events.interfaces import IEventRepository
from ....domain.records.interfaces import IEmotionalRecordRepository
from ....infrastructure.database.connection import DatabaseConnection
from ....infrastructure.database.models import DailySuggestionModel
from ....application.services.agent_service import IAgentService
```

**Path Aliases:**
No path aliases detected. Full relative imports used consistently: `from ....domain.entities.user import User`

**Absolute vs Relative:**
Relative imports required for clean architecture layers:
- Within a layer: relative (e.g., `from ..value_objects.user_profile import UserProfile`)
- Across layers (upward only): relative with appropriate depth (e.g., `from ....domain.entities.user import User`)

## Error Handling

**Patterns:**
- Custom exceptions inherit from `ApplicationException` (in `src/application/exceptions.py`)
- Specific exception types for business logic violations:
  - `ValidationException` — input validation failures
  - `UserNotFoundException` — user not found
  - `AgentServiceException` — agent service failures
  - `TaggingServiceException` — tagging failures
  - `UserKnowledgeServiceException` — knowledge service failures
  - `BusinessRuleViolationException` — business rule violations
  - `InsufficientPermissionsException` — permission checks
  - `ResourceLimitExceededException` — quota/limit violations

**Exception construction:**
All exceptions require a message, optional details dict:
```python
raise ValidationException("Message cannot be empty")
raise UserNotFoundException(user_id="123")
raise ResourceLimitExceededException(
    message="Token budget exceeded",
    resource_type="chat_tokens",
    limit=10000
)
```

**Error handling in routes:**
- HTTPException from FastAPI raised with status codes: `raise HTTPException(status_code=400, detail="email is required")`
- Middleware catches and formats: `ErrorHandlingMiddleware` converts unhandled exceptions to JSON responses
- Application exceptions caught in exception handlers and converted to JSON: status 400 for application errors, 422 for validation, 500 for unexpected

**No try-except without value:**
Async operations wrapped in try-except with logging:
```python
try:
    response = await self.agent_service.send_message(...)
except Exception as e:
    logger.error(f"Error in send_message: {e}", exc_info=True)
    raise
```

## Logging

**Framework:** Standard `logging` module with `logging.getLogger(__name__)`

**Patterns:**
- Every module imports logger at top: `logger = logging.getLogger(__name__)`
- Log levels used:
  - `logger.info()` — entry points, completed operations, state changes
  - `logger.warning()` — recoverable issues, fallbacks: `logger.warning(f"Crisis detected for user {user_id}")`
  - `logger.error()` — exceptions with `exc_info=True` for stack traces: `logger.error(f"Error: {e}", exc_info=True)`
  - `logger.debug()` — low-level operations (rarely used)

**Logging in specific areas:**
- Services: log initialization, method entry, important decisions
- Use cases: log operation start with user context, result state, token usage
- Middleware: log request/response, errors with stack traces
- Repositories: log query execution, returned results count
- Example: `logger.info(f"AgentChatUseCase.execute called - User: {user_id}, Agent: {agent_type}")`

**CloudWatch integration:**
Backend error logging to CloudWatch when enabled:
```python
if settings.mobile_logs_enabled:
    cw = CloudWatchLogger()
    cw.put_events(user_hash, [{'event': 'backend.error', ...}])
```

## Comments

**When to Comment:**
- Module-level docstrings required for all files explaining purpose
- Complex business logic that isn't obvious from code structure
- Rationale for workarounds or unusual patterns
- NOT for obvious code: `user.activate()` doesn't need comment

**JSDoc/TSDoc:**
Not used in this Python codebase. Use descriptive docstrings at module and class level only:
```python
"""
Core User domain entity with business logic
"""
```

**Docstring style:**
Triple-quoted module docstrings at file start:
```python
"""
Entity/Service name

One-line summary.

Longer explanation if complex.
"""
```

## Function Design

**Size:** Keep functions under 50 lines. Larger operations split into helper methods.

**Parameters:**
- Use dataclasses (DTOs) for multiple related parameters instead of `**kwargs`
- Dependency injection via constructor (`__init__`), not function parameters
- Optional parameters use `Optional[]` with `None` defaults
- UUID fields always typed as `UUID`, never strings

**Return Values:**
- Return DTOs/value objects, never raw dictionaries from public methods
- Methods like `to_dict()` convert to dictionaries for API serialization
- Async methods always return awaitable results

**Example async pattern:**
```python
async def execute(self, user_id: UUID, message: str) -> ChatResponse:
    try:
        response = await self.agent_service.send_message(user_id, agent_type, message)
        return response
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise
```

## Module Design

**Exports:**
- Only interfaces and main classes exported from module `__init__.py` files
- Use `from .module_name import ClassName` not `from . import *`

**Barrel Files:**
Routers explicitly imported in `src/presentation/api/routers/__init__.py`:
```python
from .auth import router as auth_router
from .chat import router as chat_router
```

**Layered structure:**
- `domain/` — business logic only, no framework imports
- `application/` — use cases, DTOs, service interfaces
- `infrastructure/` — implementations (SQLAlchemy, Redis, OpenAI), database models
- `presentation/` — FastAPI routers, middleware, dependency injection

**No circular imports:**
Dependency flows upward only: `presentation` → `infrastructure` → `application` → `domain`. Never reversed.

---

*Convention analysis: 2026-03-19*
