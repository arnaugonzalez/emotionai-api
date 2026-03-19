# Testing Patterns

**Analysis Date:** 2026-03-19

## Test Framework

**Runner:**
- pytest 7.4.0+
- Config: No `pytest.ini` or `setup.cfg` detected — uses pytest defaults
- Async support: `pytest-asyncio` 0.21.0+ (in requirements.txt)

**Assertion Library:**
- Python standard `assert` statements (no external assertion library detected)

**Run Commands:**
```bash
pytest                              # Run all tests
pytest -v                           # Verbose output with test names
pytest tests/                       # Run specific test directory
pytest -k "test_name"               # Run tests matching pattern
pytest --asyncio-mode=auto          # Run async tests (may be needed)
```

**Note:** Test discovery follows pytest defaults — looks for `test_*.py` or `*_test.py` files, test classes named `Test*`, test functions named `test_*`.

## Test File Organization

**Location:**
- Co-located with source code in `tests/` directory at project root
- Mirror source structure: `tests/domain/`, `tests/application/`, `tests/infrastructure/`
- Directory structure matches `src/` organization

**Naming:**
- Test files: `test_[module_name].py` (e.g., `test_user.py`, `test_chat_dtos.py`)
- Test functions: `test_[feature]_[scenario]()` (e.g., `test_user_creation_success()`, `test_invalid_message_raises_error()`)
- Test classes: Optional but could use `Test[Feature]` if grouping tests (e.g., `TestUserEntity`, `TestChatResponse`)

**Structure:**
```
tests/
├── __pycache__/          # Pytest cache directory
├── domain/               # Domain layer tests
│   ├── entities/
│   │   └── test_user.py
│   ├── value_objects/
│   │   ├── test_user_profile.py
│   │   └── test_agent_personality.py
│   ├── events/
│   │   └── test_domain_events.py
│   └── chat/
│       └── test_entities.py
├── application/          # Application layer tests
│   ├── dtos/
│   │   ├── test_chat_dtos.py
│   │   └── test_profile_dtos.py
│   ├── chat/
│   │   └── use_cases/
│   │       └── test_agent_chat_use_case.py
│   └── usage/
│       └── use_cases/
│           └── test_get_monthly_usage_use_case.py
└── infrastructure/       # Infrastructure tests (currently minimal)
```

**Current state:** Test source files (`.py`) exist in pyc-compiled form in `tests/` but source is not in version control — only `.pyc` files persist. This indicates tests were compiled but source files were removed or not committed.

## Test Structure

**Typical test pattern (inferred from pyc naming and codebase analysis):**

```python
import pytest
from uuid import uuid4

from src.domain.entities.user import User
from src.application.dtos.chat_dtos import ChatRequest


class TestChatRequest:
    """Test suite for ChatRequest DTO validation"""

    def test_valid_chat_request_creation(self):
        """ChatRequest accepts valid message"""
        user_id = uuid4()
        request = ChatRequest(
            user_id=user_id,
            message="How are you feeling today?",
            agent_type="therapy"
        )
        assert request.user_id == user_id
        assert request.message == "How are you feeling today?"

    def test_empty_message_raises_error(self):
        """ChatRequest raises ValueError for empty message"""
        user_id = uuid4()
        with pytest.raises(ValueError):
            ChatRequest(user_id=user_id, message="", agent_type="therapy")

    def test_message_too_long_raises_error(self):
        """ChatRequest raises ValueError for message > 2000 chars"""
        user_id = uuid4()
        long_message = "x" * 2001
        with pytest.raises(ValueError):
            ChatRequest(user_id=user_id, message=long_message)

    def test_invalid_agent_type_raises_error(self):
        """ChatRequest raises ValueError for unknown agent type"""
        user_id = uuid4()
        with pytest.raises(ValueError):
            ChatRequest(
                user_id=user_id,
                message="Hello",
                agent_type="unknown_agent"
            )


@pytest.mark.asyncio
async def test_user_chat_use_case_execution():
    """Test full chat use case flow"""
    # Setup: Create mock services/repos
    # Act: Execute use case
    # Assert: Verify response shape and content
    pass
```

**Setup pattern:**
- No dedicated fixtures detected (no `conftest.py` with shared fixtures)
- Likely using inline test setup with `pytest.fixture` decorators if needed
- Manual object creation in each test preferred

**Async testing:**
- Use `@pytest.mark.asyncio` decorator for async test functions
- Tests awaiting async functions should be decorated with this marker
- Asyncio mode: likely configured in pytest defaults or via `--asyncio-mode=auto` flag

## Mocking

**Framework:** Standard `unittest.mock` from Python standard library (expected based on dependencies)

**Patterns:**
```python
from unittest.mock import Mock, AsyncMock, patch

# Mock a service
mock_agent_service = Mock(spec=IAgentService)
mock_agent_service.send_message = AsyncMock(return_value=ChatResponse(...))

# Mock database
mock_db = Mock()
mock_session = AsyncMock()
mock_db.get_session.return_value.__aenter__.return_value = mock_session

# Patch a module function
with patch('src.infrastructure.services.openai_tagging_service.openai.AsyncOpenAI') as mock_openai:
    mock_openai.return_value.chat.completions.create.return_value = ...
```

**What to Mock:**
- External service calls: OpenAI API, Redis connections, database sessions
- Repository layer in application tests: Replace with mocks that return test data
- Event bus: Replace with mock that records published events
- LLM services: Return synthetic responses
- Time-dependent operations: Mock `datetime.now()` if test timing matters

**What NOT to Mock:**
- Domain entities: Use real domain objects for testing business logic
- Value objects: Create real instances (they're immutable and deterministic)
- DTOs: Create real instances with test data (they're just data containers)
- Repository interfaces: Test real implementation with test database if possible
- Clean architecture boundaries: Test through public interfaces to catch integration issues

## Fixtures and Factories

**Test Data:**
Based on domain code, create reusable test builders:

```python
@pytest.fixture
def sample_user_id():
    """Provide a test UUID"""
    return UUID("550e8400-e29b-41d4-a716-446655440000")

@pytest.fixture
def sample_user():
    """Create a User entity for testing"""
    return User(
        id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        email="test@example.com",
        hashed_password="hashed_password_string",
        is_active=True
    )

@pytest.fixture
def sample_chat_request():
    """Create a ChatRequest DTO for testing"""
    return ChatRequest(
        user_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
        message="I'm feeling anxious",
        agent_type="therapy",
        context={}
    )

@pytest.fixture
def sample_user_profile():
    """Create a UserProfile value object"""
    return UserProfile(
        name="John Doe",
        age=30,
        gender="male",
        goals=["manage anxiety", "improve sleep"],
        concerns=["work stress"],
        communication_style="direct"
    )
```

**Location:**
- Shared fixtures in `tests/conftest.py` if created (currently doesn't exist)
- Local fixtures in test modules: `@pytest.fixture` decorator in same file
- Factory functions in `tests/factories/` if needed for complex object construction

## Coverage

**Requirements:** Not enforced (no coverage configuration detected)

**View Coverage:**
```bash
pytest --cov=src --cov-report=html    # Generate HTML coverage report
pytest --cov=src --cov-report=term    # Terminal coverage summary
```

**Coverage report location:** `htmlcov/index.html` or displayed in terminal

## Test Types

**Unit Tests:**
- Scope: Single domain object, single function, or single DTO
- Approach: Test business logic in isolation using real domain objects, mock external dependencies
- Examples: Testing `User.update_profile()` business logic, testing DTO validation in `__post_init__`, testing value object methods like `UserProfile.is_complete()`
- No database required; pure function testing

**Integration Tests:**
- Scope: Full use case flow through layers; repository → service → application → presentation
- Approach: Mock external services (OpenAI API, Redis) but use real repositories and domain objects
- Database: Use test database or in-memory SQLite for repository tests
- Example: Test `AgentChatUseCase.execute()` with mock agent service but real conversation repository

**E2E Tests:**
- Scope: Full HTTP endpoint through FastAPI router, dependency injection, all layers
- Approach: Mock only external services (OpenAI API, Redis); use test database
- Framework: Could use `TestClient` from FastAPI or `httpx` for async requests
- Not currently present in codebase

```python
from fastapi.testclient import TestClient

def test_chat_endpoint_e2e(client: TestClient):
    """Test POST /v1/api/chat endpoint"""
    response = client.post(
        "/v1/api/chat",
        json={"message": "How are you?", "agent_type": "therapy"},
        headers={"Authorization": "Bearer <test_token>"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "agent_type" in data
```

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_repository_get_user_by_id():
    """Test async repository method"""
    # Create mock database connection
    mock_db = AsyncMock()
    repo = SqlAlchemyUserRepository(mock_db)

    # Mock the session and query result
    mock_session = AsyncMock()
    mock_db.get_session.return_value.__aenter__.return_value = mock_session
    mock_db.get_session.return_value.__aexit__.return_value = None

    # Configure the mock result
    mock_result = Mock()
    mock_result.scalar_one_or_none.return_value = UserModel(id=uuid4(), email="test@test.com")
    mock_session.execute.return_value = mock_result

    # Execute and assert
    user = await repo.get_by_id(uuid4())
    assert user is not None
```

**Error Testing:**
```python
def test_validation_exception_with_details():
    """Test ValidationException includes context"""
    with pytest.raises(ValidationException) as exc_info:
        raise ValidationException(
            "Email is required",
            field="email",
            value=None
        )

    assert exc_info.value.message == "Email is required"
    assert exc_info.value.field == "email"

@pytest.mark.asyncio
async def test_use_case_raises_user_not_found():
    """Test use case raises appropriate exception"""
    # Setup mocks to return None user
    mock_repo = Mock(spec=IUserRepository)
    mock_repo.get_by_id = AsyncMock(return_value=None)

    use_case = SomeUseCase(user_repository=mock_repo)

    # Should raise exception
    with pytest.raises(UserNotFoundException):
        await use_case.execute(user_id=uuid4())
```

**Parametrized Testing:**
```python
import pytest

@pytest.mark.parametrize("invalid_agent_type", [
    "unknown",
    "invalid_type",
    "",
    123,
])
def test_chat_request_rejects_invalid_agent_types(invalid_agent_type):
    """Test ChatRequest validation for various invalid agent types"""
    with pytest.raises(ValueError):
        ChatRequest(
            user_id=uuid4(),
            message="Hello",
            agent_type=invalid_agent_type
        )
```

## Test Database Setup

**Approach (expected, not explicitly configured):**
- Use SQLite in-memory database for tests: `DATABASE_URL="sqlite:///:memory:"`
- Or use separate test PostgreSQL database configured in test environment
- Before each test: Run migrations or create schema
- After each test: Rollback or drop tables

**Example setup in conftest.py (if needed):**
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture
async def test_db():
    """Create test database and run migrations"""
    engine = create_engine("sqlite:///:memory:")
    # Create schema
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(engine)
```

## Current Testing Status

**Test files present but not tracked:**
- Test source files (`.py`) not in version control
- Only `.pyc` compiled bytecode files present in `tests/` directories
- Suggests tests existed but were removed from tracking or not yet implemented in current branch

**Compilation evidence:**
- `test_agent_chat_use_case.cpython-312-pytest-9.0.2.pyc` in `tests/application/chat/use_cases/__pycache__/`
- `test_chat_dtos.cpython-312-pytest-9.0.2.pyc` in `tests/application/dtos/__pycache__/`
- Multiple other test bytecode files present

**Next steps:**
- Implement test suite following patterns above
- Place test files in `tests/` directory structure
- Commit test files to version control
- Add pytest configuration if special settings needed

---

*Testing analysis: 2026-03-19*
