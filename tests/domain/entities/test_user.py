from uuid import uuid4

from src.domain.entities.user import User
from src.domain.value_objects.agent_personality import AgentPersonality


def test_update_profile_sets_profile_updates_timestamp_and_adds_event():
    user = User(email="a@b.com", hashed_password="hash")
    old_updated = user.updated_at

    user.update_profile({"name": "Ana", "age": 30, "gender": "female", "goals": ["sleep"]})

    assert user.profile.name == "Ana"
    assert user.updated_at >= old_updated
    assert len(user.get_domain_events()) == 1
    assert user.get_domain_events()[0].event_type == "user_profile_updated"


def test_change_agent_personality_changes_only_when_different():
    user = User(email="a@b.com", hashed_password="hash")
    initial_updated = user.updated_at

    user.change_agent_personality(AgentPersonality.ANALYTICAL_PRACTICAL)
    assert user.agent_personality == AgentPersonality.ANALYTICAL_PRACTICAL
    assert user.updated_at >= initial_updated

    updated_once = user.updated_at
    user.change_agent_personality(AgentPersonality.ANALYTICAL_PRACTICAL)
    assert user.updated_at == updated_once


def test_activate_deactivate_and_domain_events_helpers():
    user = User(email="a@b.com", hashed_password="hash")

    user.deactivate()
    assert user.is_active is False

    user.activate()
    assert user.is_active is True

    user._add_domain_event("evt")
    events = user.get_domain_events()
    assert events == ["evt"]
    events.append("other")
    assert user.get_domain_events() == ["evt"]

    user.clear_domain_events()
    assert user.get_domain_events() == []


def test_user_equality_and_hash_based_on_id():
    uid = uuid4()
    u1 = User(id=uid, email="a@b.com", hashed_password="h")
    u2 = User(id=uid, email="x@y.com", hashed_password="h2")
    u3 = User(email="z@z.com", hashed_password="h3")

    assert u1 == u2
    assert u1 != u3
    assert hash(u1) == hash(u2)
