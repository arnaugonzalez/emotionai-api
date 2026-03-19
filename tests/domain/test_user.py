"""
Unit tests for the User domain entity.

Domain layer is pure Python — no frameworks, no IO, no mocks needed.
Every test constructs User objects directly and asserts business behaviour.

Known bugs (documented with xfail):
- update_profile crashes: UserProfileUpdatedEvent requires event_id/occurred_at/event_type
  which are not provided by the User.update_profile() call.
- is_profile_complete() returns None instead of False for an empty profile because
  `name and age and gender` evaluates to None (not False) when name is None.
"""

import pytest
from uuid import UUID, uuid4
from datetime import datetime, timezone

from src.domain.entities.user import User
from src.domain.value_objects.agent_personality import AgentPersonality
from src.domain.value_objects.user_profile import UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(**kwargs) -> User:
    """Create a minimal valid User; override any field via kwargs."""
    defaults = {
        "email": "alice@example.com",
        "hashed_password": "hashed_secret",
    }
    defaults.update(kwargs)
    return User(**defaults)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_user_default_construction():
    """A User created with only email/password has sensible defaults."""
    user = make_user()

    assert isinstance(user.id, UUID)
    assert user.email == "alice@example.com"
    assert user.hashed_password == "hashed_secret"
    assert user.is_active is True
    assert user.agent_personality == AgentPersonality.EMPATHETIC_SUPPORTIVE
    assert isinstance(user.profile, UserProfile)
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


def test_user_explicit_id_is_preserved():
    """When an explicit UUID is supplied it is NOT replaced during __post_init__."""
    fixed_id = uuid4()
    user = make_user(id=fixed_id)
    assert user.id == fixed_id


def test_user_id_is_unique_across_instances():
    """Two users created without an explicit ID receive different UUIDs."""
    user_a = make_user()
    user_b = make_user()
    assert user_a.id != user_b.id


def test_user_created_with_inactive_flag():
    """Users can be created already deactivated (e.g. when loading from DB)."""
    user = make_user(is_active=False)
    assert user.is_active is False


def test_user_email_stored_as_provided():
    """Email is stored exactly as given — no normalisation in entity."""
    user = make_user(email="User@EXAMPLE.COM")
    assert user.email == "User@EXAMPLE.COM"


def test_user_created_at_is_utc():
    """created_at should carry UTC timezone info."""
    user = make_user()
    assert user.created_at.tzinfo is not None


def test_user_empty_domain_events_on_construction():
    """
    User created via make_user() has no pending domain events.

    The __post_init__ only fires UserCreatedEvent when self.id is falsy, but
    id is always set by the default_factory=uuid4 before __post_init__ runs.
    """
    user = make_user()
    assert user.get_domain_events() == []


# ---------------------------------------------------------------------------
# activate / deactivate
# ---------------------------------------------------------------------------

def test_deactivate_sets_is_active_false():
    user = make_user()
    user.deactivate()
    assert user.is_active is False


def test_activate_sets_is_active_true():
    user = make_user(is_active=False)
    user.activate()
    assert user.is_active is True


def test_deactivate_updates_updated_at():
    user = make_user()
    before = user.updated_at
    user.deactivate()
    assert user.updated_at >= before


def test_activate_updates_updated_at():
    user = make_user(is_active=False)
    before = user.updated_at
    user.activate()
    assert user.updated_at >= before


def test_deactivate_then_reactivate():
    """Round-trip: deactivate then activate should leave user active."""
    user = make_user()
    user.deactivate()
    user.activate()
    assert user.is_active is True


# ---------------------------------------------------------------------------
# change_agent_personality
# ---------------------------------------------------------------------------

def test_change_agent_personality_updates_value():
    user = make_user()
    user.change_agent_personality(AgentPersonality.ANALYTICAL_PRACTICAL)
    assert user.agent_personality == AgentPersonality.ANALYTICAL_PRACTICAL


def test_change_agent_personality_updates_updated_at():
    user = make_user()
    before = user.updated_at
    user.change_agent_personality(AgentPersonality.MINDFUL_CONTEMPLATIVE)
    assert user.updated_at >= before


def test_change_agent_personality_same_value_noop():
    """Changing to the same personality should not advance updated_at."""
    user = make_user()
    original_updated = user.updated_at
    user.change_agent_personality(AgentPersonality.EMPATHETIC_SUPPORTIVE)
    assert user.updated_at == original_updated


def test_can_cycle_through_all_personalities():
    """All AgentPersonality values can be set without error."""
    user = make_user()
    for personality in AgentPersonality:
        user.change_agent_personality(personality)
    assert user.agent_personality == list(AgentPersonality)[-1]


# ---------------------------------------------------------------------------
# update_profile — known bug: UserProfileUpdatedEvent cannot be instantiated
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason=(
        "update_profile() raises TypeError because UserProfileUpdatedEvent "
        "requires event_id/occurred_at/event_type positional args that "
        "User.update_profile() does not supply. "
        "Fix: give DomainEvent subclass fields default_factory values."
    ),
)
def test_update_profile_replaces_profile():
    user = make_user()
    user.update_profile({"name": "Alice", "age": 30, "gender": "female"})
    assert user.profile.name == "Alice"
    assert user.profile.age == 30


@pytest.mark.xfail(
    strict=True,
    reason="update_profile() crashes before updating profile — see test_update_profile_replaces_profile",
)
def test_update_profile_emits_event():
    from src.domain.events.domain_events import UserProfileUpdatedEvent
    user = make_user()
    user.clear_domain_events()
    user.update_profile({"name": "Carol"})
    events = user.get_domain_events()
    assert len(events) == 1
    assert isinstance(events[0], UserProfileUpdatedEvent)


# ---------------------------------------------------------------------------
# is_profile_complete — known bug: returns None instead of False
# ---------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    reason=(
        "is_profile_complete() returns None (not False) for an empty profile. "
        "UserProfile.is_complete() has: `basic_info_complete = self.name and self.age and self.gender` "
        "which evaluates to None when name is None, so `None and (...)` is None. "
        "Fix: cast to bool — `bool(self.name) and bool(self.age) and bool(self.gender)`."
    ),
)
def test_is_profile_complete_false_for_empty_profile():
    user = make_user()
    result = user.is_profile_complete()
    assert result is False  # currently returns None


# ---------------------------------------------------------------------------
# get_agent_preferences
# ---------------------------------------------------------------------------

def test_get_agent_preferences_returns_dict():
    user = make_user()
    prefs = user.get_agent_preferences()
    assert isinstance(prefs, dict)


def test_get_agent_preferences_keys():
    user = make_user()
    prefs = user.get_agent_preferences()
    assert "personality" in prefs
    assert "goals" in prefs
    assert "concerns" in prefs
    assert "preferred_activities" in prefs
    assert "communication_style" in prefs


def test_get_agent_preferences_personality_value():
    user = make_user()
    prefs = user.get_agent_preferences()
    assert prefs["personality"] == AgentPersonality.EMPATHETIC_SUPPORTIVE.value


def test_get_agent_preferences_empty_lists_by_default():
    user = make_user()
    prefs = user.get_agent_preferences()
    assert prefs["goals"] == []
    assert prefs["concerns"] == []
    assert prefs["preferred_activities"] == []


# ---------------------------------------------------------------------------
# Domain events management
# ---------------------------------------------------------------------------

def test_get_domain_events_returns_copy():
    """Mutating the returned list must not change internal state."""
    user = make_user()
    user._add_domain_event("fake_event")  # inject a synthetic event
    events = user.get_domain_events()
    events.clear()
    # Internal list must still contain the injected event
    assert len(user.get_domain_events()) > 0


def test_clear_domain_events_empties_list():
    user = make_user()
    user._add_domain_event("fake_event")
    user.clear_domain_events()
    assert user.get_domain_events() == []


def test_multiple_events_accumulate():
    user = make_user()
    user._add_domain_event("event_1")
    user._add_domain_event("event_2")
    assert len(user.get_domain_events()) == 2


# ---------------------------------------------------------------------------
# Equality and hashing
# ---------------------------------------------------------------------------

def test_equality_same_id():
    fixed_id = uuid4()
    user_a = make_user(id=fixed_id)
    user_b = make_user(id=fixed_id, email="different@example.com")
    assert user_a == user_b


def test_equality_different_ids():
    assert make_user() != make_user()


def test_inequality_with_non_user():
    user = make_user()
    assert user != "not a user"
    assert user != 42
    assert user is not None


def test_hash_same_id():
    fixed_id = uuid4()
    user_a = make_user(id=fixed_id)
    user_b = make_user(id=fixed_id)
    assert hash(user_a) == hash(user_b)


def test_user_can_be_used_in_set():
    fixed_id = uuid4()
    user_a = make_user(id=fixed_id)
    user_b = make_user(id=fixed_id)
    user_set = {user_a, user_b}
    assert len(user_set) == 1


def test_users_with_different_ids_are_distinct_in_set():
    user_a = make_user()
    user_b = make_user()
    user_set = {user_a, user_b}
    assert len(user_set) == 2
