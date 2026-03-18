from src.domain.value_objects.agent_personality import AgentPersonality


def test_from_string_valid_value_maps_to_enum():
    value = AgentPersonality.from_string("analytical_practical")
    assert value == AgentPersonality.ANALYTICAL_PRACTICAL


def test_from_string_invalid_falls_back_to_default():
    value = AgentPersonality.from_string("unknown")
    assert value == AgentPersonality.EMPATHETIC_SUPPORTIVE


def test_personality_metadata_methods_return_expected_content():
    p = AgentPersonality.CREATIVE_EXPRESSIVE
    assert "creative" in p.get_description().lower() or "artistic" in p.get_description().lower()
    assert p.get_system_prompt_addition() != ""
    prefs = p.get_default_preferences()
    assert prefs["response_tone"] == "inspiring"
    assert "suggestion_style" in prefs


def test_get_all_descriptions_contains_all_enum_values():
    descriptions = AgentPersonality.get_all_descriptions()
    assert len(descriptions) == len(AgentPersonality)
    for personality in AgentPersonality:
        assert personality.value in descriptions
