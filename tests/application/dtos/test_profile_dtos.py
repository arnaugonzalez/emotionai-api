from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.application.dtos.profile_dtos import (
    EmergencyContact,
    MedicalInfo,
    TherapyPreferences,
    UserProfileRequest,
    UserProfileResponse,
    TherapyContextRequest,
    TherapyContextResponse,
    ProfileStatusResponse,
)


# ---------------------------------------------------------------------------
# Existing tests (updated "calm" → "supportive" since validator now enforces
# an allowed-values list)
# ---------------------------------------------------------------------------

def test_nested_profile_dtos_valid_instantiation():
    contact = EmergencyContact(
        name="Jane",
        relationship="sister",
        phone="123456",
        email="jane@example.com",
    )
    med = MedicalInfo(conditions=["asthma"], medications=["m1"], allergies=["a1"])
    prefs = TherapyPreferences(communication_style="supportive", focus_areas=["sleep"], goals="reduce anxiety")

    req = UserProfileRequest(
        first_name="Ana",
        emergency_contact=contact,
        medical_info=med,
        therapy_preferences=prefs,
        user_profile_data={"personality_type": "INFJ"},
        terms_accepted=True,
    )

    assert req.first_name == "Ana"
    assert req.emergency_contact.email == "jane@example.com"
    assert req.medical_info.conditions == ["asthma"]
    assert req.therapy_preferences.focus_areas == ["sleep"]


def test_emergency_contact_invalid_email_raises_validation_error():
    with pytest.raises(Exception):
        EmergencyContact(name="x", relationship="friend", phone="1", email="not-an-email")


def test_profile_response_and_context_response_models():
    now = datetime.now(timezone.utc)
    resp = UserProfileResponse(
        id="u1",
        email="u@example.com",
        is_profile_complete=True,
        created_at=now,
        updated_at=now,
    )
    assert resp.id == "u1"
    assert resp.is_profile_complete is True

    ctx_req = TherapyContextRequest(therapy_context={"k": "v"}, ai_insights={"i": 1})
    assert ctx_req.therapy_context == {"k": "v"}

    ctx_resp = TherapyContextResponse(last_updated=now, context_summary="ok")
    assert ctx_resp.context_summary == "ok"

    status = ProfileStatusResponse(has_profile=True, profile_completeness=85.0, missing_fields=["age"])
    assert status.has_profile is True
    assert status.missing_fields == ["age"]


# ---------------------------------------------------------------------------
# TestUserProfileRequest — @model_validator tests
# ---------------------------------------------------------------------------

class TestUserProfileRequest:
    def test_all_none_fields_raises_validation_error(self):
        """UserProfileRequest with all None fields must fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            UserProfileRequest()
        assert "at least one profile field must be provided" in str(exc_info.value).lower()

    def test_single_field_provided_succeeds(self):
        """UserProfileRequest with only first_name should pass."""
        req = UserProfileRequest(first_name="John")
        assert req.first_name == "John"

    def test_terms_accepted_only_succeeds(self):
        """UserProfileRequest with only terms_accepted should pass."""
        req = UserProfileRequest(terms_accepted=True)
        assert req.terms_accepted is True

    def test_multiple_fields_provided_succeeds(self):
        """UserProfileRequest with several non-None fields should pass."""
        req = UserProfileRequest(first_name="Alice", last_name="Smith", occupation="Engineer")
        assert req.last_name == "Smith"


# ---------------------------------------------------------------------------
# TestTherapyPreferences — @field_validator tests
# ---------------------------------------------------------------------------

class TestTherapyPreferences:
    def test_invalid_communication_style_raises_validation_error(self):
        """Unknown communication_style must fail validation."""
        with pytest.raises(ValidationError):
            TherapyPreferences(communication_style="invalid_style")

    def test_supportive_style_succeeds(self):
        prefs = TherapyPreferences(communication_style="supportive")
        assert prefs.communication_style == "supportive"

    def test_direct_style_succeeds(self):
        prefs = TherapyPreferences(communication_style="direct")
        assert prefs.communication_style == "direct"

    def test_analytical_style_succeeds(self):
        prefs = TherapyPreferences(communication_style="analytical")
        assert prefs.communication_style == "analytical"

    def test_casual_style_succeeds(self):
        prefs = TherapyPreferences(communication_style="casual")
        assert prefs.communication_style == "casual"

    def test_formal_style_succeeds(self):
        prefs = TherapyPreferences(communication_style="formal")
        assert prefs.communication_style == "formal"

    def test_none_communication_style_succeeds(self):
        """None is allowed — communication_style is optional."""
        prefs = TherapyPreferences(communication_style=None)
        assert prefs.communication_style is None

    def test_default_communication_style_is_none(self):
        """Default value for communication_style should be None."""
        prefs = TherapyPreferences()
        assert prefs.communication_style is None


# ---------------------------------------------------------------------------
# TestProfileStatusResponse — @field_validator tests
# ---------------------------------------------------------------------------

class TestProfileStatusResponse:
    def test_negative_completeness_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ProfileStatusResponse(has_profile=True, profile_completeness=-1)

    def test_over_100_completeness_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ProfileStatusResponse(has_profile=True, profile_completeness=101)

    def test_valid_completeness_succeeds(self):
        resp = ProfileStatusResponse(has_profile=True, profile_completeness=75.5)
        assert resp.profile_completeness == 75.5

    def test_zero_completeness_succeeds(self):
        resp = ProfileStatusResponse(has_profile=False, profile_completeness=0)
        assert resp.profile_completeness == 0

    def test_100_completeness_succeeds(self):
        resp = ProfileStatusResponse(has_profile=True, profile_completeness=100)
        assert resp.profile_completeness == 100


# ---------------------------------------------------------------------------
# TestUserProfileResponse — model_config tests
# ---------------------------------------------------------------------------

class TestUserProfileResponse:
    def test_has_model_config_with_from_attributes(self):
        """UserProfileResponse must have from_attributes=True for ORM compatibility."""
        assert hasattr(UserProfileResponse, "model_config")

    def test_from_attributes_is_true(self):
        assert UserProfileResponse.model_config["from_attributes"] is True
