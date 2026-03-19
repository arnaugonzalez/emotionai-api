"""
Unit tests for the UserProfile value object.

UserProfile is a frozen dataclass — immutable after creation.
All tests use direct construction and assertion; zero mocks.
"""

import pytest
from src.domain.value_objects.user_profile import UserProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def minimal_profile(**kwargs) -> UserProfile:
    """Return a UserProfile with only the supplied kwargs set."""
    return UserProfile(**kwargs)


def complete_profile() -> UserProfile:
    """Return a fully-populated UserProfile for completeness checks."""
    return UserProfile(
        name="Alice",
        age=28,
        gender="female",
        occupation="engineer",
        personality_type="INTJ",
        goals=["reduce anxiety"],
        concerns=["work stress"],
        preferred_activities=["yoga"],
        therapy_goals=["build resilience"],
        wellness_goals=["sleep better"],
        coping_strategies=["journaling"],
        mindfulness_practices=["meditation"],
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_empty_profile_construction():
    """UserProfile can be created with all defaults."""
    profile = UserProfile()
    assert profile.name is None
    assert profile.age is None
    assert profile.goals == []
    assert profile.concerns == []


def test_profile_with_all_fields():
    """All fields can be set at construction time."""
    profile = complete_profile()
    assert profile.name == "Alice"
    assert profile.age == 28
    assert profile.gender == "female"
    assert profile.occupation == "engineer"
    assert profile.personality_type == "INTJ"


def test_profile_list_fields_default_to_empty_list():
    """List fields default to [] (not None)."""
    profile = UserProfile()
    list_fields = [
        "relaxation_tools", "goals", "concerns", "preferred_activities",
        "therapy_goals", "wellness_goals", "coping_strategies",
        "mindfulness_practices", "crisis_contacts",
    ]
    for field_name in list_fields:
        assert getattr(profile, field_name) == [], f"{field_name} should default to []"


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_profile_is_frozen():
    """UserProfile is a frozen dataclass — direct attribute mutation raises."""
    profile = UserProfile(name="Alice")
    with pytest.raises(Exception):  # FrozenInstanceError is a subclass of AttributeError
        profile.name = "Bob"  # type: ignore[misc]


def test_update_returns_new_instance():
    """update() returns a new UserProfile, leaving the original unchanged."""
    original = UserProfile(name="Alice")
    updated = original.update(name="Bob")
    assert updated.name == "Bob"
    assert original.name == "Alice"  # original is unchanged


def test_update_preserves_other_fields():
    """update() only changes the specified fields."""
    original = UserProfile(name="Alice", age=30, gender="female")
    updated = original.update(age=31)
    assert updated.name == "Alice"
    assert updated.gender == "female"
    assert updated.age == 31


# ---------------------------------------------------------------------------
# is_complete
# ---------------------------------------------------------------------------

def test_is_complete_false_for_empty_profile():
    """
    An empty UserProfile is not complete.

    NOTE: is_complete() currently returns None (not False) because
    `self.name and self.age and self.gender` short-circuits on None.
    We test the falsy contract: the return value must be falsy.
    """
    profile = UserProfile()
    assert not profile.is_complete()


def test_is_complete_true_with_basic_info_and_goals():
    """name + age + gender + at least one goal → complete."""
    profile = UserProfile(name="Alice", age=28, gender="female", goals=["reduce stress"])
    assert profile.is_complete()


def test_is_complete_true_with_basic_info_and_concerns():
    """concerns (not goals) can satisfy the context_complete branch."""
    profile = UserProfile(name="Bob", age=35, gender="male", concerns=["sleep issues"])
    assert profile.is_complete()


def test_is_complete_false_missing_age():
    """Missing age means basic_info_complete is falsy."""
    profile = UserProfile(name="Alice", gender="female", goals=["goal1"])
    assert not profile.is_complete()


# ---------------------------------------------------------------------------
# get_completeness_score
# ---------------------------------------------------------------------------

def test_completeness_score_empty_is_zero():
    profile = UserProfile()
    assert profile.get_completeness_score() == 0.0


def test_completeness_score_full_is_one():
    profile = complete_profile()
    assert profile.get_completeness_score() == 1.0


def test_completeness_score_partial():
    """Partial profile yields a score between 0 and 1."""
    profile = UserProfile(name="Alice", age=28, gender="female")
    score = profile.get_completeness_score()
    assert 0.0 < score < 1.0


def test_completeness_score_out_of_twelve():
    """Score = completed / 12. One field = 1/12."""
    profile = UserProfile(name="Alice")
    assert profile.get_completeness_score() == pytest.approx(1 / 12)


# ---------------------------------------------------------------------------
# get_missing_fields
# ---------------------------------------------------------------------------

def test_get_missing_fields_all_missing_for_empty_profile():
    profile = UserProfile()
    missing = profile.get_missing_fields()
    assert "name" in missing
    assert "age" in missing
    assert "gender" in missing


def test_get_missing_fields_complete_profile_is_empty():
    profile = complete_profile()
    missing = profile.get_missing_fields()
    assert missing == []


def test_get_missing_fields_partial():
    profile = UserProfile(name="Alice", age=28)
    missing = profile.get_missing_fields()
    assert "name" not in missing
    assert "age" not in missing
    assert "gender" in missing


# ---------------------------------------------------------------------------
# get_all_goals
# ---------------------------------------------------------------------------

def test_get_all_goals_combines_three_lists():
    profile = UserProfile(
        goals=["goal_a"],
        therapy_goals=["therapy_b"],
        wellness_goals=["wellness_c"],
    )
    all_goals = profile.get_all_goals()
    assert "goal_a" in all_goals
    assert "therapy_b" in all_goals
    assert "wellness_c" in all_goals
    assert len(all_goals) == 3


def test_get_all_goals_empty_for_empty_profile():
    profile = UserProfile()
    assert profile.get_all_goals() == []


# ---------------------------------------------------------------------------
# has_crisis_support
# ---------------------------------------------------------------------------

def test_has_crisis_support_false_by_default():
    profile = UserProfile()
    assert profile.has_crisis_support() is False


def test_has_crisis_support_true_with_contact():
    profile = UserProfile(crisis_contacts=[{"name": "Dr. Smith", "phone": "+1234"}])
    assert profile.has_crisis_support() is True


# ---------------------------------------------------------------------------
# from_dict / to_dict roundtrip
# ---------------------------------------------------------------------------

def test_from_dict_basic_fields():
    data = {"name": "Alice", "age": 30, "gender": "female"}
    profile = UserProfile.from_dict(data)
    assert profile.name == "Alice"
    assert profile.age == 30
    assert profile.gender == "female"


def test_from_dict_list_fields_default_to_empty():
    profile = UserProfile.from_dict({})
    assert profile.goals == []
    assert profile.concerns == []


def test_to_dict_roundtrip():
    profile = complete_profile()
    restored = UserProfile.from_dict(profile.to_dict())
    assert restored == profile


def test_to_dict_contains_all_expected_keys():
    profile = UserProfile()
    d = profile.to_dict()
    expected_keys = {
        "name", "age", "gender", "occupation", "country", "personality_type",
        "relaxation_time", "selfcare_frequency", "relaxation_tools",
        "has_previous_mental_health_app_experience", "therapy_chat_history_preference",
        "goals", "concerns", "preferred_activities", "therapy_goals",
        "wellness_goals", "coping_strategies", "mindfulness_practices",
        "communication_style", "timezone", "preferred_session_length", "crisis_contacts",
    }
    assert expected_keys == set(d.keys())


# ---------------------------------------------------------------------------
# get_personalization_context
# ---------------------------------------------------------------------------

def test_get_personalization_context_returns_dict():
    profile = UserProfile()
    ctx = profile.get_personalization_context()
    assert isinstance(ctx, dict)


def test_get_personalization_context_includes_completeness_score():
    profile = UserProfile()
    ctx = profile.get_personalization_context()
    assert "completeness_score" in ctx
    assert ctx["completeness_score"] == 0.0


def test_get_personalization_context_has_crisis_support_flag():
    profile = UserProfile()
    ctx = profile.get_personalization_context()
    assert "has_crisis_support" in ctx
    assert ctx["has_crisis_support"] is False
