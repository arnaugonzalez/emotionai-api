"""
Shared test fixtures for the EmotionAI API test suite.

This conftest.py is the single fixture home for all test slices.
It provides:
  - async_engine: session-scoped in-memory SQLite engine via aiosqlite
  - mock_container: function-scoped mock of ApplicationContainer
  - MockRepository: base class for per-test repository fakes
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from sqlalchemy.orm import DeclarativeBase


# ---------------------------------------------------------------------------
# Minimal declarative base for SQLite fixture
#
# NOTE: The production ORM models in src/infrastructure/database/models.py use
# PostgreSQL-specific column types (UUID, JSONB, ARRAY) that are incompatible
# with SQLite. This base is intentionally separate — it is extended in later
# test slices with SQLite-compatible table definitions for integration tests.
# ---------------------------------------------------------------------------

class TestBase(DeclarativeBase):
    """SQLAlchemy declarative base for in-memory test tables."""
    pass


# ---------------------------------------------------------------------------
# Fixture 1: Async SQLite engine (session-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
async def async_engine() -> AsyncEngine:
    """
    Create an async in-memory SQLite engine for the test session.

    Session-scoped so the engine is created once and reused across all tests
    in a session, which is fast and avoids repeated setup costs.

    Yields the engine and drops all tables on teardown.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.drop_all)

    await engine.dispose()


# ---------------------------------------------------------------------------
# Fixture 2: Mock ApplicationContainer factory (function-scoped)
#
# Mirrors the exact attribute names from src/infrastructure/container.py
# so routers and use cases can be tested by injecting this mock.
# ---------------------------------------------------------------------------

class MockApplicationContainer:
    """
    Test double for ApplicationContainer.

    Attribute names are taken directly from the @dataclass definition in
    src/infrastructure/container.py. Each attribute is an AsyncMock so that
    tests can await calls and inspect arguments without touching real I/O.
    """

    def __init__(self) -> None:
        # Core infrastructure (sync stubs — no I/O in tests)
        self.settings = MagicMock()
        self.database = MagicMock()
        self.llm_factory = MagicMock()

        # Repositories
        self.user_repository = AsyncMock()
        self.emotional_repository = AsyncMock()
        self.breathing_repository = AsyncMock()
        self.conversation_repository = AsyncMock()
        self.event_repository = AsyncMock()
        self.analytics_repository = AsyncMock()
        self.token_usage_repository = AsyncMock()

        # Services
        self.agent_service = AsyncMock()
        self.event_bus = AsyncMock()
        self.tagging_service = AsyncMock()
        self.user_knowledge_service = AsyncMock()
        self.similarity_search_service = AsyncMock()
        self.profile_service = AsyncMock()

        # Use cases
        self.agent_chat_use_case = AsyncMock()
        self.get_monthly_usage_use_case = AsyncMock()


@pytest.fixture()
def mock_container() -> MockApplicationContainer:
    """
    Return a fresh MockApplicationContainer for each test function.

    Function-scoped so that one test's side-effects (e.g., configuring return
    values on a mock) do not leak into the next test.
    """
    return MockApplicationContainer()


# ---------------------------------------------------------------------------
# Utility 3: MockRepository base class (not a fixture — import directly)
#
# Usage:
#   from tests.conftest import MockRepository
#
#   class FakeUserRepo(MockRepository):
#       pass
#
# ---------------------------------------------------------------------------

class MockRepository:
    """
    Base class for hand-written repository fakes.

    Provides AsyncMock for the four canonical repository operations.
    Subclass this in per-slice test helpers when you need finer control
    than a bare AsyncMock provides (e.g., pre-loaded in-memory data).
    """

    def __init__(self) -> None:
        self.get_by_id = AsyncMock()
        self.save = AsyncMock()
        self.delete = AsyncMock()
        self.list_all = AsyncMock()
