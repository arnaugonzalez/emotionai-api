from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.application.dtos.chat_dtos import (
    ChatRequest,
    ChatResponse,
    AgentStatusResponse,
    EmotionalRecordRequest,
    BreathingSessionRequest,
    UserProfileUpdateRequest,
    UserRegistrationRequest,
    UserLoginRequest,
    TokenResponse,
    ConversationHistoryResponse,
)


def test_chat_request_validation_paths():
    uid = uuid4()
    ChatRequest(user_id=uid, message="hello", agent_type="therapy")

    with pytest.raises(ValueError):
        ChatRequest(user_id=uid, message="   ", agent_type="therapy")
    with pytest.raises(ValueError):
        ChatRequest(user_id=uid, message="x" * 2001, agent_type="therapy")
    with pytest.raises(ValueError):
        ChatRequest(user_id=uid, message="ok", agent_type="other")


def test_chat_response_defaults_crisis_factory_and_to_dict():
    resp = ChatResponse(message="m", agent_type="therapy", user_message="u")
    assert resp.timestamp is not None
    data = resp.to_dict()
    assert data["agent_type"] == "therapy"

    crisis = ChatResponse.create_crisis_response("urgent")
    assert crisis.is_crisis_response is True
    assert crisis.agent_type == "crisis"


def test_additional_dtos_validation_and_to_dict():
    uid = uuid4()

    status = AgentStatusResponse(active=True, agent_type="therapy")
    assert status.to_dict()["active"] is True

    EmotionalRecordRequest(user_id=uid, emotion_type="sad", intensity=5)
    with pytest.raises(ValueError):
        EmotionalRecordRequest(user_id=uid, emotion_type="sad", intensity=11)
    with pytest.raises(ValueError):
        EmotionalRecordRequest(user_id=uid, emotion_type="", intensity=5)

    BreathingSessionRequest(user_id=uid, pattern_name="box", duration_seconds=10, rating=8.0)
    with pytest.raises(ValueError):
        BreathingSessionRequest(user_id=uid, pattern_name="box", duration_seconds=-1)
    with pytest.raises(ValueError):
        BreathingSessionRequest(user_id=uid, pattern_name="box", duration_seconds=1, rating=10.5)

    UserProfileUpdateRequest(user_id=uid, profile_data={"k": "v"})
    with pytest.raises(ValueError):
        UserProfileUpdateRequest(user_id=uid, profile_data={})

    UserRegistrationRequest(email="a@b.com", password="123456", first_name="A", last_name="B")
    with pytest.raises(ValueError):
        UserRegistrationRequest(email="bad", password="123456", first_name="A", last_name="B")
    with pytest.raises(ValueError):
        UserRegistrationRequest(email="a@b.com", password="123", first_name="A", last_name="B")
    with pytest.raises(ValueError):
        UserRegistrationRequest(email="a@b.com", password="123456", first_name="", last_name="B")

    UserLoginRequest(email="a@b.com", password="123")
    with pytest.raises(ValueError):
        UserLoginRequest(email="bad", password="123")
    with pytest.raises(ValueError):
        UserLoginRequest(email="a@b.com", password="")

    token = TokenResponse(access_token="t", token_type="bearer", expires_in=3600, user={"id": "u1"})
    assert token.to_dict()["token_type"] == "bearer"

    now = datetime.now(timezone.utc)
    hist = ConversationHistoryResponse(
        id="c1",
        agent_type="therapy",
        title="t",
        created_at=now,
        last_message_at=now,
        message_count=1,
    )
    assert hist.to_dict()["id"] == "c1"
