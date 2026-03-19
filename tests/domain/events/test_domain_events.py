from datetime import datetime, timezone
from uuid import uuid4

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


def test_domain_event_to_dict_serializes_timestamp():
    event = DomainEvent(
        event_id="evt-1",
        occurred_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        event_type="custom",
    )
    data = event.to_dict()

    assert data["event_id"] == "evt-1"
    assert data["event_type"] == "custom"
    assert data["occurred_at"].startswith("2026-01-01")


def test_specific_events_keep_explicit_values_and_types():
    user_id = uuid4()
    ts = datetime.now(timezone.utc)
    old_profile = UserProfile(name="A", age=20, gender="f")
    new_profile = UserProfile(name="A", age=21, gender="f")

    e1 = UserCreatedEvent(event_id="1", occurred_at=ts, event_type="user_created", user_id=user_id, email="a@b.com")
    e2 = UserProfileUpdatedEvent(
        event_id="2",
        occurred_at=ts,
        event_type="user_profile_updated",
        user_id=user_id,
        old_profile=old_profile,
        new_profile=new_profile,
    )
    e3 = AgentConversationStartedEvent(
        event_id="3",
        occurred_at=ts,
        event_type="agent_conversation_started",
        user_id=user_id,
        agent_type="therapy",
        session_id="s1",
    )
    e4 = EmotionalRecordCreatedEvent(
        event_id="4",
        occurred_at=ts,
        event_type="emotional_record_created",
        user_id=user_id,
        emotion_type="sad",
        intensity=6,
        context="work",
    )
    e5 = UserDataTaggedEvent(
        event_id="5",
        occurred_at=ts,
        event_type="user_data_tagged",
        user_id=user_id,
        data_type="message",
        data_id="m1",
        extracted_tags=["anxiety"],
        tag_confidence=0.9,
    )
    e6 = UserProfileInsightsUpdatedEvent(
        event_id="6",
        occurred_at=ts,
        event_type="user_profile_insights_updated",
        user_id=user_id,
        insights_added=["sleep"],
        tags_updated=True,
        behavioral_patterns_detected=False,
    )

    assert e1.email == "a@b.com"
    assert e2.new_profile.age == 21
    assert e3.session_id == "s1"
    assert e4.intensity == 6
    assert e5.extracted_tags == ["anxiety"]
    assert e6.tags_updated is True
