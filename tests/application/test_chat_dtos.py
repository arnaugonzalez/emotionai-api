"""
Unit tests for Pydantic DTO validator behavior.

These tests verify that DTOs use Pydantic v2 BaseModel with @field_validator,
producing ValidationError (not ValueError) for invalid inputs.
"""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from src.application.dtos.chat_dtos import (
    ChatRequest,
    ChatResponse,
    EmotionalRecordRequest,
    BreathingSessionRequest,
    UserRegistrationRequest,
)
from src.presentation.api.routers.chat import ChatApiRequest


# ---------------------------------------------------------------------------
# TestChatRequest
# ---------------------------------------------------------------------------


class TestChatRequest:
    """Tests for ChatRequest Pydantic validator behavior."""

    def test_empty_message_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError) as exc_info:
            ChatRequest(user_id=uid, message="")
        errors = exc_info.value.errors()
        fields = [e["loc"][0] for e in errors]
        assert "message" in fields

    def test_whitespace_only_message_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError):
            ChatRequest(user_id=uid, message="   ")

    def test_message_too_long_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError):
            ChatRequest(user_id=uid, message="x" * 2001)

    def test_invalid_agent_type_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError):
            ChatRequest(user_id=uid, message="hello", agent_type="invalid")

    def test_valid_therapy_agent_type_succeeds(self):
        uid = uuid4()
        req = ChatRequest(user_id=uid, message="hello", agent_type="therapy")
        assert req.agent_type == "therapy"

    def test_valid_wellness_agent_type_succeeds(self):
        uid = uuid4()
        req = ChatRequest(user_id=uid, message="hello", agent_type="wellness")
        assert req.agent_type == "wellness"


# ---------------------------------------------------------------------------
# TestEmotionalRecordRequest
# ---------------------------------------------------------------------------


class TestEmotionalRecordRequest:
    """Tests for EmotionalRecordRequest Pydantic validator behavior."""

    def test_intensity_zero_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError):
            EmotionalRecordRequest(user_id=uid, emotion_type="happy", intensity=0)

    def test_intensity_eleven_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError):
            EmotionalRecordRequest(user_id=uid, emotion_type="happy", intensity=11)

    def test_valid_intensity_five_succeeds(self):
        uid = uuid4()
        req = EmotionalRecordRequest(user_id=uid, emotion_type="happy", intensity=5)
        assert req.intensity == 5

    def test_empty_emotion_type_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError):
            EmotionalRecordRequest(user_id=uid, emotion_type="", intensity=5)


# ---------------------------------------------------------------------------
# TestBreathingSessionRequest
# ---------------------------------------------------------------------------


class TestBreathingSessionRequest:
    """Tests for BreathingSessionRequest Pydantic validator behavior."""

    def test_negative_duration_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError):
            BreathingSessionRequest(
                user_id=uid, pattern_name="box", duration_seconds=-1
            )

    def test_rating_out_of_range_raises_validation_error(self):
        uid = uuid4()
        with pytest.raises(ValidationError):
            BreathingSessionRequest(
                user_id=uid, pattern_name="box", duration_seconds=60, rating=11.0
            )

    def test_valid_session_succeeds(self):
        uid = uuid4()
        req = BreathingSessionRequest(
            user_id=uid, pattern_name="box", duration_seconds=60, rating=8.0
        )
        assert req.duration_seconds == 60


# ---------------------------------------------------------------------------
# TestUserRegistrationRequest
# ---------------------------------------------------------------------------


class TestUserRegistrationRequest:
    """Tests for UserRegistrationRequest Pydantic validator behavior."""

    def test_invalid_email_raises_validation_error(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequest(
                email="invalid", password="secret1", first_name="A", last_name="B"
            )

    def test_password_too_short_raises_validation_error(self):
        with pytest.raises(ValidationError):
            UserRegistrationRequest(
                email="a@b.com", password="short", first_name="A", last_name="B"
            )

    def test_valid_registration_succeeds(self):
        req = UserRegistrationRequest(
            email="a@b.com", password="secret1", first_name="Alice", last_name="Bob"
        )
        assert req.email == "a@b.com"


# ---------------------------------------------------------------------------
# TestChatResponse
# ---------------------------------------------------------------------------


class TestChatResponse:
    """Tests for ChatResponse Pydantic behavior."""

    def test_model_dump_returns_expected_keys(self):
        resp = ChatResponse(message="hello", agent_type="therapy", user_message="hi")
        data = resp.model_dump()
        assert "message" in data
        assert "agent_type" in data
        assert "timestamp" in data

    def test_create_crisis_response_sets_flag(self):
        crisis = ChatResponse.create_crisis_response("urgent help needed")
        assert crisis.is_crisis_response is True
        assert crisis.agent_type == "crisis"


# ---------------------------------------------------------------------------
# TestChatApiRequest
# ---------------------------------------------------------------------------


class TestChatApiRequest:
    """Tests for ChatApiRequest Pydantic validator behavior."""

    def test_empty_message_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ChatApiRequest(message="", agent_type="therapy")

    def test_message_too_long_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ChatApiRequest(message="x" * 701, agent_type="therapy")

    def test_valid_message_succeeds(self):
        req = ChatApiRequest(message="hello", agent_type="therapy")
        assert req.message == "hello"

    def test_invalid_agent_type_raises_validation_error(self):
        with pytest.raises(ValidationError):
            ChatApiRequest(message="hello", agent_type="invalid_type")
