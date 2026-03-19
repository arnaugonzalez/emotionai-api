"""
Unit tests for the AgentPersonality value object (Enum).

AgentPersonality is a pure Python Enum with business methods — zero IO, zero mocks.
"""

import pytest
from src.domain.value_objects.agent_personality import AgentPersonality


# ---------------------------------------------------------------------------
# Enum membership
# ---------------------------------------------------------------------------

def test_all_expected_personalities_exist():
    """Five personalities are defined."""
    values = {p.value for p in AgentPersonality}
    assert values == {
        "empathetic_supportive",
        "encouraging_motivational",
        "analytical_practical",
        "mindful_contemplative",
        "creative_expressive",
    }


def test_each_personality_is_distinct():
    """No two enum members share the same value."""
    values = [p.value for p in AgentPersonality]
    assert len(values) == len(set(values))


# ---------------------------------------------------------------------------
# get_description
# ---------------------------------------------------------------------------

def test_get_description_returns_non_empty_string_for_all():
    for personality in AgentPersonality:
        desc = personality.get_description()
        assert isinstance(desc, str)
        assert len(desc) > 0, f"{personality.name} has an empty description"


def test_empathetic_description_mentions_empathy():
    desc = AgentPersonality.EMPATHETIC_SUPPORTIVE.get_description()
    assert "empathy" in desc.lower() or "warm" in desc.lower() or "validat" in desc.lower()


def test_analytical_description_mentions_structure_or_solutions():
    desc = AgentPersonality.ANALYTICAL_PRACTICAL.get_description()
    assert "structured" in desc.lower() or "solution" in desc.lower() or "practical" in desc.lower()


# ---------------------------------------------------------------------------
# get_system_prompt_addition
# ---------------------------------------------------------------------------

def test_get_system_prompt_addition_returns_non_empty_for_all():
    for personality in AgentPersonality:
        prompt = personality.get_system_prompt_addition()
        assert isinstance(prompt, str)
        assert len(prompt) > 0, f"{personality.name} has an empty system prompt addition"


def test_mindful_prompt_mentions_mindfulness():
    prompt = AgentPersonality.MINDFUL_CONTEMPLATIVE.get_system_prompt_addition()
    assert "mindful" in prompt.lower() or "awareness" in prompt.lower() or "present" in prompt.lower()


# ---------------------------------------------------------------------------
# get_default_preferences
# ---------------------------------------------------------------------------

def test_get_default_preferences_returns_dict_for_all():
    for personality in AgentPersonality:
        prefs = personality.get_default_preferences()
        assert isinstance(prefs, dict)
        assert len(prefs) > 0, f"{personality.name} has empty default preferences"


def test_empathetic_preference_has_warm_tone():
    prefs = AgentPersonality.EMPATHETIC_SUPPORTIVE.get_default_preferences()
    assert prefs.get("response_tone") == "warm"


def test_analytical_preference_has_structured_suggestion_style():
    prefs = AgentPersonality.ANALYTICAL_PRACTICAL.get_default_preferences()
    assert prefs.get("suggestion_style") == "structured"


def test_all_preferences_contain_expected_keys():
    required_keys = {"response_tone", "validation_frequency", "suggestion_style"}
    for personality in AgentPersonality:
        prefs = personality.get_default_preferences()
        assert required_keys.issubset(prefs.keys()), (
            f"{personality.name} preferences missing keys: {required_keys - prefs.keys()}"
        )


# ---------------------------------------------------------------------------
# from_string
# ---------------------------------------------------------------------------

def test_from_string_exact_match():
    p = AgentPersonality.from_string("empathetic_supportive")
    assert p == AgentPersonality.EMPATHETIC_SUPPORTIVE


def test_from_string_uppercase_input_is_lowercased():
    p = AgentPersonality.from_string("ANALYTICAL_PRACTICAL")
    assert p == AgentPersonality.ANALYTICAL_PRACTICAL


def test_from_string_invalid_value_falls_back_to_default():
    p = AgentPersonality.from_string("does_not_exist")
    assert p == AgentPersonality.EMPATHETIC_SUPPORTIVE


def test_from_string_empty_string_falls_back_to_default():
    p = AgentPersonality.from_string("")
    assert p == AgentPersonality.EMPATHETIC_SUPPORTIVE


# ---------------------------------------------------------------------------
# get_all_descriptions (class method)
# ---------------------------------------------------------------------------

def test_get_all_descriptions_returns_all_five():
    descriptions = AgentPersonality.get_all_descriptions()
    assert len(descriptions) == 5


def test_get_all_descriptions_keys_are_string_values():
    descriptions = AgentPersonality.get_all_descriptions()
    for key in descriptions:
        assert isinstance(key, str)
        # Key should be a valid personality value
        AgentPersonality(key)  # must not raise


def test_get_all_descriptions_values_are_non_empty_strings():
    descriptions = AgentPersonality.get_all_descriptions()
    for value in descriptions.values():
        assert isinstance(value, str) and len(value) > 0
