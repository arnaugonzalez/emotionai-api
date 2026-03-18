from src.domain.value_objects.user_profile import UserProfile


def test_is_complete_true_with_basic_and_goals():
    profile = UserProfile(name="Ana", age=30, gender="female", goals=["sleep better"])
    assert profile.is_complete() is True


def test_is_complete_false_when_basic_info_missing():
    profile = UserProfile(age=30, gender="female", goals=["sleep better"])
    assert profile.is_complete() is False


def test_get_completeness_score_expected_ratio():
    profile = UserProfile(name="Ana", age=30, gender="female", goals=["g1"], concerns=["c1"])
    # name, age, gender, goals, concerns = 5 / 12
    assert profile.get_completeness_score() == 5 / 12


def test_get_missing_fields_contains_expected_items():
    profile = UserProfile(name="Ana", age=30)
    missing = profile.get_missing_fields()
    assert "gender" in missing
    assert "general_goals" in missing
    assert "concerns" in missing


def test_from_dict_to_dict_round_trip_and_update_immutability():
    data = {
        "name": "Ana",
        "age": 30,
        "gender": "female",
        "goals": ["sleep better"],
    }
    profile = UserProfile.from_dict(data)
    assert profile.to_dict()["name"] == "Ana"

    updated = profile.update(occupation="Engineer")
    assert updated.occupation == "Engineer"
    assert profile.occupation is None


def test_get_personalization_context_merges_all_goals_and_metadata():
    profile = UserProfile(
        name="Ana",
        age=30,
        personality_type="INFJ",
        goals=["g1"],
        therapy_goals=["tg1"],
        wellness_goals=["wg1"],
        crisis_contacts=[{"name": "friend", "phone": "123"}],
    )
    context = profile.get_personalization_context()
    assert context["goals"] == ["g1", "tg1", "wg1"]
    assert context["has_crisis_support"] is True
    assert 0.0 <= context["completeness_score"] <= 1.0
