# Coding Conventions

**Analysis Date:** 2026-03-19

## Naming Patterns

**Files:**
- Router files: `[feature]_router.py` (e.g., `chat.py`, `auth.py`) → located in `src/presentation/api/routers/`
- Service files: `[service_name]_service.py` (e.g., `langchain_agent_service.py`, `openai_tagging_service.py`) → located in `src/infrastructure/services/`
- Repository files: `sqlalchemy_[entity]_repository.py` (e.g., `sqlalchemy_user_repository.py`) → located in `src/infrastructure/repositories/`
- Domain entities: `[entity].py` (e.g., `user.py`) → located in `src/domain/entities/`
- Value objects: `[concept].py` (e.g., `user_profile.py`, `agent_personality.py`) → located in `src/domain/value_objects/`
- DTOs: `[domain]_dtos.py` (e.g., `chat_dtos.py`, `profile_dtos.py`) → located in `src/application/dtos/`
- Use cases: `[verb]_[entity]_use_case.py` (e.g., `agent_chat_use_case.py`, `get_monthly_usage_use_case.py`) → located in `src/application/[feature]/use_cases/`

**Functions:**
- Use `snake_case` for all function names: `get_user_id()`, `send_message()`, `_convert_to_dict()`
- Prefix private/internal functions with single underscore: `_model_to_entity()`, `_parse_jwt()`, `_add_domain_event()`
- Async functions are regular `async def` with same naming: `async def get_by_id()`, `async def execute()`
- Handler functions at endpoints: `async def [verb]_[resource]()` (e.g., `async def chat_with_agent()`, `async def get_agent_status()`)
- Dependency providers: `get_[service_name]()` (e.g., `get_container()`, `get_current_user_id()`, `get_profile_service()`)

**Variables:**
- Use `snake_case` for all variables and parameters: `user_id`, `agent_type`, `conversation_id`, `hashed_password`
- Private module-level variables: `_default_value`, `_cache_dict`
- Type hints always present: `user_id: UUID`, `message: str`, `context: Optional[Dict[str, Any]]`

**Classes:**
- Use `PascalCase` for all classes: `User`, `ChatResponse`, `ApplicationException`, `SqlAlchemyUserRepository`
- Exception classes: `[ProblemArea]Exception` (e.g., `ValidationException`, `UserNotFoundException`, `AgentServiceException`)
- Repository interfaces: `I[Entity]Repository` (e.g., `IUserRepository`, `IEmotionalRecordRepository`)
- Service interfaces: `I[Service]` (e.g., `IAgentService`, `IEventBus`, `ITaggingService`)
- DTOs: `[Domain]Request`/`[Domain]Response` (e.g., `ChatRequest`, `ChatResponse`, `AgentStatusRequest`)
- Value objects: `[Concept]` (e.g., `UserProfile`, `AgentPersonality`)
- SQLAlchemy models: `[Entity]Model` (e.g., `UserModel`, `ConversationModel`)

**Constants:**
- Use `UPPER_SNAKE_CASE` for constants: `MAX_MESSAGE_LENGTH = 700`, `MENTAL_HEALTH_URGENCY_KEYWORDS = [...]`
- Field defaults in dataclasses: `agent_type: str = "therapy"` (lowercase for default values)

## Code Style

**Formatting:**
- No explicit linter/formatter configuration detected
- Manual formatting observed: 4-space indentation consistently used throughout
- Line length: typically under 100-120 characters based on observed code
- Blank lines: 2 blank lines between top-level definitions (classes/functions), 1 blank line between methods

**Linting:**
- No `.flake8`, `.pylintrc`, or linting config files detected
- Linting and formatting packages available in `requirements.txt` (black, isort) but not configured/enforced

**Imports Structure:**
Organize imports in the following order:

1. **Standard library**: `import asyncio`, `from typing import ...`, `from uuid import UUID`, `from datetime import ...`
2. **Third-party packages**: `from fastapi import ...`, `from sqlalchemy import ...`, `from pydantic import ...`, `import jwt`, `import logging`
3. **Local domain imports**: `from ...domain.entities.user import User`, `from ...domain.value_objects.user_profile import UserProfile`
4. **Local application imports**: `from ...application.services.agent_service import IAgentService`, `from ...application.dtos.chat_dtos import ChatResponse`
5. **Local infrastructure imports**: `from ...infrastructure.database.models import UserModel`, `from ...infrastructure.config.settings import settings`
6. **Local presentation imports**: `from .deps import get_container`, `from ....infrastructure.container import ApplicationContainer`

Use relative imports (e.g., `from ....domain.entities.user` rather than absolute path imports).

**Relative import depth pattern:**
- From `src/presentation/api/routers/chat.py`: use 4 dots `....domain` or `....application`
- From `src/infrastructure/repositories/sqlalchemy_user_repository.py`: use 3 dots `...domain`
- Use count matching the depth difference between current location and target package

## Error Handling

**Patterns:**
- **Domain/Application layer**: Raise domain-specific `ApplicationException` subclasses with semantic names:
  - `ValidationException` for input validation failures
  - `UserNotFoundException` for missing users
  - `AgentServiceException` for agent operation failures
  - `BusinessRuleViolationException` for business logic violations
  - All exceptions accept optional contextual metadata: `details: Optional[Dict[str, Any]]`
  - See `src/application/exceptions.py` for full list

- **Presentation layer (FastAPI routers)**: Convert exceptions to HTTP responses:
  ```python
  except ApplicationException as e:
      raise HTTPException(
          status_code=status.HTTP_400_BAD_REQUEST,
          detail={
              "error": e.__class__.__name__,
              "message": e.message,
              "details": e.details
          }
      )
  ```

- **Unexpected errors**: Log with full traceback and return generic 500 error:
  ```python
  except Exception as e:
      logger.error(f"Unexpected error in [endpoint]: {str(e)}", exc_info=True)
      raise HTTPException(
          status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
          detail={
              "error": "InternalServerError",
              "message": "An unexpected error occurred",
              "details": {...}
          }
      )
  ```

- **No silent failures**: Always log exceptions before re-raising
- **Async exception handling**: Try-except blocks present in async functions work identically to sync functions
- **Database operation failures**: Wrapped in try-except with logging, converted to `RepositoryException` if needed

## Logging

**Framework:** Standard Python `logging` module

**Configuration:** Set in `main.py`:
```python
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

**Patterns:**
- Get logger per module: `logger = logging.getLogger(__name__)`
- Log at appropriate levels:
  - `logger.info()` for business-relevant events (endpoint calls, use case execution)
  - `logger.debug()` for detailed debugging (method entry/exit if needed)
  - `logger.warning()` for recoverable issues (crisis detection, empty results)
  - `logger.error()` for failures requiring attention, always include context
  - Use `exc_info=True` for exception logging: `logger.error(f"Error: {e}", exc_info=True)`

- **Example patterns from codebase:**
  - `logger.info(f"Chat request received - User: {current_user_id}, Agent: {payload.agent_type}")` - structured context in message
  - `logger.error(f"Agent service missing 'send_message' method. Available methods: {dir(self.agent_service)}")` - helpful debug info
  - `logger.warning(f"Response object missing 'message' attribute. Response: {response}")` - unexpected but non-fatal
  - Avoid logging sensitive data (passwords, full tokens)

## Comments

**When to Comment:**
- Module/file level: Always include docstring explaining the module's purpose, located immediately after opening (see all modules in codebase)
- Classes: Include docstring after class declaration explaining the class purpose and usage
- Complex business logic: Comment non-obvious logic that implements business rules
- Public methods: Include docstring explaining parameters, return type, and exceptions raised
- Private methods: Docstring optional but recommended
- TODO/FIXME: Acceptable but should reference specific issues or include context
- Avoid commenting obvious code: `x = x + 1  # increment x` is unnecessary

**Docstring/TSDoc:**
- Use triple-quoted strings `"""..."""` for all module, class, and method docstrings
- Format: Describe what the function does, then parameter details if complex:
  ```python
  def update_profile(self, profile_data: Dict[str, Any]) -> None:
      """Update user profile with business validation"""
  ```
- Return type in signature (`:` after parameters, `->` for return type)
- No structured @param/@return blocks observed; keep docstrings concise

## Function Design

**Size:**
- Typical functions 20-50 lines observed
- Use-case execution methods can be longer (80+ lines) if logically coherent
- Prefer breaking complex logic into helper functions (private `_` functions)

**Parameters:**
- Type hints required: `def get_by_id(self, user_id: UUID) -> Optional[User]:`
- Use dataclasses/DTO objects for multiple related parameters rather than individual params
- Optional parameters with defaults at end: `agent_type: str = "therapy"`
- Domain entities passed as parameters, not IDs when possible

**Return Values:**
- Explicit return type hints required
- Return domain entities from repositories, not ORM models
- Return DTOs from routers, not domain entities or ORM models
- Use `Optional[T]` for nullable returns
- Consider returning tuples for multiple related values: `(user, is_new: bool)`

## Module Design

**Exports:**
- Router modules export a router object: `router = APIRouter(prefix="/chat")`
- Service modules export class definitions; instantiation in container
- Repository modules export class definitions only
- No `__all__` patterns observed; all public-facing classes/functions are implicitly exported

**Barrel Files:**
- Observed in `src/presentation/api/routers/__init__.py`: aggregates router imports for convenient loading
- Used in `src/application/[feature]/__init__.py`: sometimes empty, sometimes re-exports
- Pattern: import routers/services and make available from single import: `from .chat_router import router as chat_router`

## Async Patterns

**Consistency:** All database and service calls are `async def`; no synchronous blocking calls in async handlers.

**Function signatures:**
```python
async def execute(self, user_id: UUID, ...) -> Any:
    # all awaits inside
    result = await some_async_service.call()
    return result
```

**Dependency injection:**
```python
async def some_endpoint(
    current_user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    # both Depends() work in async endpoints
```

## Value Objects

**Immutability:** Use `@dataclass(frozen=True)` for value objects:
```python
@dataclass(frozen=True)
class ChatRequest:
    user_id: UUID
    message: str
```

**Validation:** Implement in `__post_init__()` for dataclass validation:
```python
def __post_init__(self):
    if not self.message or len(self.message.strip()) == 0:
        raise ValueError("Message cannot be empty")
```

## Domain Layer (No Framework Imports)

**Critical rule:** `src/domain/` must never import FastAPI, SQLAlchemy, Pydantic, or LangChain

**What's allowed:**
- Python standard library
- Domain value objects and entities
- Abstract base classes and protocols
- Custom exception classes (in domain)

**Example violation to avoid:**
```python
# WRONG - in src/domain/entities/user.py:
from sqlalchemy import Column, String  # ← NO
from fastapi import HTTPException       # ← NO

# CORRECT:
from dataclasses import dataclass
from typing import Optional
```

---

*Convention analysis: 2026-03-19*
