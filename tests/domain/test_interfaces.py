"""
Unit tests for domain repository and service interfaces.

Purpose: These tests instantiate minimal concrete implementations of each
abstract interface to verify the interface contract is callable and to
satisfy coverage on the abstract method stubs.

Interfaces are pure ABC contracts — no business logic. These tests document
the expected method signatures for future implementers.
"""

import pytest
from uuid import UUID, uuid4
from typing import List, Optional, Dict, Any

from src.domain.users.interfaces import IUserRepository
from src.domain.events.interfaces import IEventRepository
from src.domain.chat.interfaces import IAgentConversationRepository
from src.domain.analytics.interfaces import IAnalyticsRepository
from src.domain.records.interfaces import IEmotionalRecordRepository
from src.domain.breathing.interfaces import IBreathingSessionRepository
from src.domain.usage.interfaces import ITokenUsageRepository
from src.domain.entities.user import User
from src.domain.events.domain_events import DomainEvent


# ---------------------------------------------------------------------------
# Minimal concrete implementations (not production code — only for tests)
# ---------------------------------------------------------------------------

class ConcreteUserRepository(IUserRepository):
    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        return None

    async def save(self, user: User) -> User:
        return user

    async def delete(self, user_id: UUID) -> bool:
        return True

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        return []

    async def exists(self, email: str) -> bool:
        return False


class ConcreteEventRepository(IEventRepository):
    async def save_event(self, event: DomainEvent) -> None:
        pass

    async def get_events_by_user(
        self, user_id: UUID, event_types: Optional[List[str]] = None
    ) -> List[DomainEvent]:
        return []

    async def get_unprocessed_events(self) -> List[DomainEvent]:
        return []

    async def mark_event_processed(self, event_id: str) -> None:
        pass


class ConcreteAgentConversationRepository(IAgentConversationRepository):
    async def save_conversation(
        self, user_id: UUID, agent_type: str, conversation_data: Dict[str, Any]
    ) -> str:
        return "conv-001"

    async def get_conversation_history(
        self, user_id: UUID, agent_type: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        return []

    async def get_conversation_summary(
        self, user_id: UUID, agent_type: str
    ) -> Optional[str]:
        return None


class ConcreteAnalyticsRepository(IAnalyticsRepository):
    async def save_agent_interaction(
        self, user_id: UUID, agent_type: str, interaction_data: Dict[str, Any]
    ) -> None:
        pass


class ConcreteEmotionalRecordRepository(IEmotionalRecordRepository):
    async def get_by_user_id(
        self, user_id: UUID, limit: Optional[int] = None, days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        return []

    async def save(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        return record_data

    async def get_emotional_patterns(self, user_id: UUID) -> Dict[str, Any]:
        return {}

    async def get_records_by_date_range(
        self, user_id: UUID, start_date: Any, end_date: Any
    ) -> List[Dict[str, Any]]:
        return []


class ConcreteBreathingRepository(IBreathingSessionRepository):
    async def get_by_user_id(
        self, user_id: UUID, limit: Optional[int] = None, days_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        return []

    async def save(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        return session_data

    async def get_session_analytics(self, user_id: UUID) -> Dict[str, Any]:
        return {}


class ConcreteTokenUsageRepository(ITokenUsageRepository):
    async def log_usage(
        self,
        user_id: UUID,
        interaction_type: str,
        total_tokens: int,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
        model: Optional[str] = None,
        data_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        pass

    async def get_monthly_usage(self, user_id: UUID, year: int, month: int) -> int:
        return 0


# ---------------------------------------------------------------------------
# IUserRepository interface contract
# ---------------------------------------------------------------------------

def test_user_repository_can_be_instantiated():
    repo = ConcreteUserRepository()
    assert repo is not None


def test_user_repository_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        IUserRepository()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# IEventRepository interface contract
# ---------------------------------------------------------------------------

def test_event_repository_can_be_instantiated():
    repo = ConcreteEventRepository()
    assert repo is not None


def test_event_repository_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        IEventRepository()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# IAgentConversationRepository interface contract
# ---------------------------------------------------------------------------

def test_agent_conversation_repository_can_be_instantiated():
    repo = ConcreteAgentConversationRepository()
    assert repo is not None


def test_agent_conversation_repository_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        IAgentConversationRepository()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# IAnalyticsRepository interface contract
# ---------------------------------------------------------------------------

def test_analytics_repository_can_be_instantiated():
    repo = ConcreteAnalyticsRepository()
    assert repo is not None


def test_analytics_repository_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        IAnalyticsRepository()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Async method signatures (smoke tests — no assertions beyond "no exception")
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_user_repo_get_by_id_returns_none():
    repo = ConcreteUserRepository()
    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_user_repo_get_by_email_returns_none():
    repo = ConcreteUserRepository()
    result = await repo.get_by_email("test@test.com")
    assert result is None


@pytest.mark.asyncio
async def test_user_repo_save_returns_user():
    repo = ConcreteUserRepository()
    user = User(email="alice@example.com", hashed_password="hash")
    saved = await repo.save(user)
    assert saved is user


@pytest.mark.asyncio
async def test_user_repo_delete_returns_bool():
    repo = ConcreteUserRepository()
    result = await repo.delete(uuid4())
    assert result is True


@pytest.mark.asyncio
async def test_user_repo_list_users_returns_list():
    repo = ConcreteUserRepository()
    result = await repo.list_users()
    assert result == []


@pytest.mark.asyncio
async def test_user_repo_exists_returns_bool():
    repo = ConcreteUserRepository()
    result = await repo.exists("test@test.com")
    assert result is False


@pytest.mark.asyncio
async def test_event_repo_get_unprocessed_returns_list():
    repo = ConcreteEventRepository()
    result = await repo.get_unprocessed_events()
    assert result == []


@pytest.mark.asyncio
async def test_agent_conversation_repo_save_returns_id():
    repo = ConcreteAgentConversationRepository()
    result = await repo.save_conversation(uuid4(), "therapy", {})
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_agent_conversation_repo_get_history_returns_list():
    repo = ConcreteAgentConversationRepository()
    result = await repo.get_conversation_history(uuid4(), "therapy")
    assert result == []


@pytest.mark.asyncio
async def test_agent_conversation_repo_get_summary_returns_none():
    repo = ConcreteAgentConversationRepository()
    result = await repo.get_conversation_summary(uuid4(), "therapy")
    assert result is None


@pytest.mark.asyncio
async def test_analytics_repo_save_does_not_raise():
    repo = ConcreteAnalyticsRepository()
    await repo.save_agent_interaction(uuid4(), "therapy", {"tokens": 100})


# ---------------------------------------------------------------------------
# IEmotionalRecordRepository interface contract
# ---------------------------------------------------------------------------

def test_emotional_record_repository_can_be_instantiated():
    repo = ConcreteEmotionalRecordRepository()
    assert repo is not None


def test_emotional_record_repository_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        IEmotionalRecordRepository()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_emotional_record_repo_get_by_user_id_returns_list():
    repo = ConcreteEmotionalRecordRepository()
    result = await repo.get_by_user_id(uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_emotional_record_repo_get_patterns_returns_dict():
    repo = ConcreteEmotionalRecordRepository()
    result = await repo.get_emotional_patterns(uuid4())
    assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_emotional_record_repo_get_date_range_returns_list():
    repo = ConcreteEmotionalRecordRepository()
    result = await repo.get_records_by_date_range(uuid4(), None, None)
    assert result == []


# ---------------------------------------------------------------------------
# IBreathingSessionRepository interface contract
# ---------------------------------------------------------------------------

def test_breathing_repository_can_be_instantiated():
    repo = ConcreteBreathingRepository()
    assert repo is not None


def test_breathing_repository_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        IBreathingSessionRepository()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_breathing_repo_get_analytics_returns_dict():
    repo = ConcreteBreathingRepository()
    result = await repo.get_session_analytics(uuid4())
    assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# ITokenUsageRepository interface contract
# ---------------------------------------------------------------------------

def test_token_usage_repository_can_be_instantiated():
    repo = ConcreteTokenUsageRepository()
    assert repo is not None


def test_token_usage_repository_cannot_instantiate_abc_directly():
    with pytest.raises(TypeError):
        ITokenUsageRepository()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_token_usage_repo_get_monthly_usage_returns_int():
    repo = ConcreteTokenUsageRepository()
    result = await repo.get_monthly_usage(uuid4(), 2026, 3)
    assert result == 0


@pytest.mark.asyncio
async def test_token_usage_repo_log_usage_does_not_raise():
    repo = ConcreteTokenUsageRepository()
    await repo.log_usage(
        user_id=uuid4(),
        interaction_type="chat",
        total_tokens=500,
        tokens_prompt=200,
        tokens_completion=300,
        model="gpt-4",
    )
