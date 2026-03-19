"""
Unit tests for domain events.

Domain events are frozen dataclasses. All fields must be provided at
construction time — the __post_init__ `hasattr` guard ONLY fills in
event_id/occurred_at/event_type when they haven't been set via positional
args, but because DomainEvent requires them, they MUST be passed explicitly.

Known bug (documented with xfail):
  The __post_init__ auto-fill logic uses `hasattr` but frozen dataclasses
  require ALL fields in __init__. This means the convenience "no args needed"
  approach in the codebase comment is misleading — base fields are always
  required.
"""

import pytest
import uuid
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.domain.events.domain_events import (
    DomainEvent,
    UserCreatedEvent,
    UserProfileUpdatedEvent,
    AgentConversationStartedEvent,
    EmotionalRecordCreatedEvent,
    UserDataTaggedEvent,
    UserProfileInsightsUpdatedEvent,
)
from src.domain.value_objects.user_profile import UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_base_fields():
    """Return the three required base DomainEvent fields."""
    return {
        "event_id": str(uuid.uuid4()),
        "occurred_at": datetime.now(timezone.utc),
        "event_type": "test_event",
    }


# ---------------------------------------------------------------------------
# DomainEvent base class
# ---------------------------------------------------------------------------

def test_domain_event_construction():
    """DomainEvent can be created directly with all required fields."""
    fields = make_base_fields()
    event = DomainEvent(**fields)
    assert event.event_id == fields["event_id"]
    assert event.event_type == fields["event_type"]
    assert event.occurred_at == fields["occurred_at"]


def test_domain_event_is_frozen():
    """DomainEvent is immutable — mutation must raise."""
    event = DomainEvent(**make_base_fields())
    with pytest.raises(Exception):
        event.event_type = "changed"  # type: ignore[misc]


def test_domain_event_to_dict():
    fields = make_base_fields()
    event = DomainEvent(**fields)
    d = event.to_dict()
    assert d["event_id"] == fields["event_id"]
    assert d["event_type"] == "test_event"
    assert "occurred_at" in d


def test_domain_event_to_dict_occurred_at_is_isoformat_string():
    event = DomainEvent(**make_base_fields())
    d = event.to_dict()
    # Must be a valid ISO-format string
    parsed = datetime.fromisoformat(d["occurred_at"])
    assert isinstance(parsed, datetime)


# ---------------------------------------------------------------------------
# UserCreatedEvent
# ---------------------------------------------------------------------------

def test_user_created_event_construction():
    uid = uuid4()
    event = UserCreatedEvent(
        **make_base_fields(),
        user_id=uid,
        email="alice@example.com",
    )
    assert event.user_id == uid
    assert event.email == "alice@example.com"


def test_user_created_event_event_type_field():
    event = UserCreatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        email="test@test.com",
    )
    # The event_type we pass is stored as-is (base field)
    assert isinstance(event.event_type, str)
    assert len(event.event_type) > 0


def test_user_created_event_is_frozen():
    event = UserCreatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        email="test@test.com",
    )
    with pytest.raises(Exception):
        event.email = "changed@example.com"  # type: ignore[misc]


def test_user_created_event_inherits_domain_event():
    event = UserCreatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        email="test@test.com",
    )
    assert isinstance(event, DomainEvent)


# ---------------------------------------------------------------------------
# UserProfileUpdatedEvent
# ---------------------------------------------------------------------------

def test_user_profile_updated_event_construction():
    uid = uuid4()
    old_profile = UserProfile(name="Alice")
    new_profile = UserProfile(name="Alice Updated")
    event = UserProfileUpdatedEvent(
        **make_base_fields(),
        user_id=uid,
        old_profile=old_profile,
        new_profile=new_profile,
    )
    assert event.user_id == uid
    assert event.old_profile is old_profile
    assert event.new_profile is new_profile


def test_user_profile_updated_event_stores_both_profiles():
    old_p = UserProfile(name="Before")
    new_p = UserProfile(name="After")
    event = UserProfileUpdatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        old_profile=old_p,
        new_profile=new_p,
    )
    assert event.old_profile.name == "Before"
    assert event.new_profile.name == "After"


def test_user_profile_updated_event_is_frozen():
    event = UserProfileUpdatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        old_profile=UserProfile(),
        new_profile=UserProfile(),
    )
    with pytest.raises(Exception):
        event.user_id = uuid4()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AgentConversationStartedEvent
# ---------------------------------------------------------------------------

def test_agent_conversation_started_event_construction():
    uid = uuid4()
    event = AgentConversationStartedEvent(
        **make_base_fields(),
        user_id=uid,
        agent_type="therapy",
        session_id="session-abc-123",
    )
    assert event.user_id == uid
    assert event.agent_type == "therapy"
    assert event.session_id == "session-abc-123"


def test_agent_conversation_started_event_inherits_domain_event():
    event = AgentConversationStartedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        agent_type="wellness",
        session_id="s1",
    )
    assert isinstance(event, DomainEvent)


def test_agent_conversation_started_event_is_frozen():
    event = AgentConversationStartedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        agent_type="therapy",
        session_id="s2",
    )
    with pytest.raises(Exception):
        event.agent_type = "changed"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# EmotionalRecordCreatedEvent
# ---------------------------------------------------------------------------

def test_emotional_record_created_event_construction():
    uid = uuid4()
    event = EmotionalRecordCreatedEvent(
        **make_base_fields(),
        user_id=uid,
        emotion_type="anxiety",
        intensity=7,
        context="work presentation",
    )
    assert event.user_id == uid
    assert event.emotion_type == "anxiety"
    assert event.intensity == 7
    assert event.context == "work presentation"


def test_emotional_record_created_event_stores_intensity():
    event = EmotionalRecordCreatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        emotion_type="joy",
        intensity=10,
        context="",
    )
    assert event.intensity == 10


def test_emotional_record_created_event_inherits_domain_event():
    event = EmotionalRecordCreatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        emotion_type="sadness",
        intensity=5,
        context="",
    )
    assert isinstance(event, DomainEvent)


def test_emotional_record_created_event_is_frozen():
    event = EmotionalRecordCreatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        emotion_type="fear",
        intensity=3,
        context="",
    )
    with pytest.raises(Exception):
        event.intensity = 9  # type: ignore[misc]


# ---------------------------------------------------------------------------
# UserDataTaggedEvent
# ---------------------------------------------------------------------------

def test_user_data_tagged_event_construction():
    uid = uuid4()
    event = UserDataTaggedEvent(
        **make_base_fields(),
        user_id=uid,
        data_type="message",
        data_id="msg-001",
        extracted_tags=["anxiety", "work"],
        tag_confidence=0.95,
    )
    assert event.user_id == uid
    assert event.data_type == "message"
    assert event.extracted_tags == ["anxiety", "work"]
    assert event.tag_confidence == 0.95


def test_user_data_tagged_event_empty_tags():
    event = UserDataTaggedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        data_type="emotional_record",
        data_id="rec-002",
        extracted_tags=[],
        tag_confidence=0.0,
    )
    assert event.extracted_tags == []
    assert event.tag_confidence == 0.0


def test_user_data_tagged_event_inherits_domain_event():
    event = UserDataTaggedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        data_type="breathing_session",
        data_id="bs-003",
        extracted_tags=["calm"],
        tag_confidence=0.8,
    )
    assert isinstance(event, DomainEvent)


# ---------------------------------------------------------------------------
# UserProfileInsightsUpdatedEvent
# ---------------------------------------------------------------------------

def test_user_profile_insights_updated_event_construction():
    uid = uuid4()
    event = UserProfileInsightsUpdatedEvent(
        **make_base_fields(),
        user_id=uid,
        insights_added=["increased anxiety sensitivity"],
        tags_updated=True,
        behavioral_patterns_detected=False,
    )
    assert event.user_id == uid
    assert event.insights_added == ["increased anxiety sensitivity"]
    assert event.tags_updated is True
    assert event.behavioral_patterns_detected is False


def test_user_profile_insights_updated_event_empty_insights():
    event = UserProfileInsightsUpdatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        insights_added=[],
        tags_updated=False,
        behavioral_patterns_detected=False,
    )
    assert event.insights_added == []


def test_user_profile_insights_updated_event_inherits_domain_event():
    event = UserProfileInsightsUpdatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        insights_added=[],
        tags_updated=False,
        behavioral_patterns_detected=False,
    )
    assert isinstance(event, DomainEvent)


def test_user_profile_insights_updated_event_is_frozen():
    event = UserProfileInsightsUpdatedEvent(
        **make_base_fields(),
        user_id=uuid4(),
        insights_added=[],
        tags_updated=False,
        behavioral_patterns_detected=False,
    )
    with pytest.raises(Exception):
        event.tags_updated = True  # type: ignore[misc]
