from datetime import datetime, timezone

import pytest

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


def test_nested_profile_dtos_valid_instantiation():
    contact = EmergencyContact(
        name="Jane",
        relationship="sister",
        phone="123456",
        email="jane@example.com",
    )
    med = MedicalInfo(conditions=["asthma"], medications=["m1"], allergies=["a1"])
    prefs = TherapyPreferences(communication_style="calm", focus_areas=["sleep"], goals="reduce anxiety")

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
