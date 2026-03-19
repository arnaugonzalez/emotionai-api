"""
Unit tests for chat domain entities: Message, Conversation, AgentContext, TherapyResponse.

Pure Python — zero IO, zero mocks.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from src.domain.chat.entities import (
    Message,
    Conversation,
    AgentContext,
    TherapyResponse,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now() -> datetime:
    return datetime.now(timezone.utc)


def make_message(**kwargs) -> Message:
    defaults = {
        "id": "msg-001",
        "conversation_id": "conv-001",
        "user_id": uuid4(),
        "content": "Hello",
        "message_type": "user",
        "metadata": {},
        "timestamp": now(),
    }
    defaults.update(kwargs)
    return Message(**defaults)


def make_conversation(**kwargs) -> Conversation:
    defaults = {
        "id": "conv-001",
        "user_id": uuid4(),
        "agent_type": "therapy",
        "title": "Session 1",
        "created_at": now(),
        "last_message_at": now(),
        "message_count": 0,
        "is_active": True,
    }
    defaults.update(kwargs)
    return Conversation(**defaults)


def make_agent_context(**kwargs) -> AgentContext:
    defaults = {
        "user_id": uuid4(),
        "agent_type": "therapy",
        "conversation_id": "conv-001",
        "recent_messages": [],
        "user_profile": {},
    }
    defaults.update(kwargs)
    return AgentContext(**defaults)


def make_therapy_response(**kwargs) -> TherapyResponse:
    defaults = {
        "message": "I hear you.",
        "agent_type": "therapy",
        "conversation_id": "conv-001",
        "timestamp": now(),
        "therapeutic_approach": "supportive",
        "emotional_tone": "empathetic",
        "follow_up_suggestions": [],
    }
    defaults.update(kwargs)
    return TherapyResponse(**defaults)


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

def test_message_construction():
    uid = uuid4()
    ts = now()
    msg = Message(
        id="m1",
        conversation_id="c1",
        user_id=uid,
        content="How are you?",
        message_type="user",
        metadata={"source": "mobile"},
        timestamp=ts,
    )
    assert msg.id == "m1"
    assert msg.conversation_id == "c1"
    assert msg.user_id == uid
    assert msg.content == "How are you?"
    assert msg.message_type == "user"
    assert msg.metadata["source"] == "mobile"
    assert msg.timestamp == ts


def test_message_types_user_assistant_system():
    for msg_type in ("user", "assistant", "system"):
        msg = make_message(message_type=msg_type)
        assert msg.message_type == msg_type


def test_message_empty_metadata():
    msg = make_message(metadata={})
    assert msg.metadata == {}


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------

def test_conversation_construction():
    uid = uuid4()
    conv = Conversation(
        id="conv-1",
        user_id=uid,
        agent_type="wellness",
        title="Day 1",
        created_at=now(),
        last_message_at=now(),
        message_count=5,
        is_active=True,
    )
    assert conv.id == "conv-1"
    assert conv.user_id == uid
    assert conv.agent_type == "wellness"
    assert conv.title == "Day 1"
    assert conv.message_count == 5
    assert conv.is_active is True


def test_conversation_inactive():
    conv = make_conversation(is_active=False)
    assert conv.is_active is False


def test_conversation_message_count_zero():
    conv = make_conversation(message_count=0)
    assert conv.message_count == 0


# ---------------------------------------------------------------------------
# AgentContext
# ---------------------------------------------------------------------------

def test_agent_context_construction():
    uid = uuid4()
    ctx = AgentContext(
        user_id=uid,
        agent_type="therapy",
        conversation_id="c1",
        recent_messages=[],
        user_profile={"name": "Alice"},
    )
    assert ctx.user_id == uid
    assert ctx.agent_type == "therapy"
    assert ctx.conversation_id == "c1"
    assert ctx.user_profile == {"name": "Alice"}


def test_agent_context_crisis_indicators_defaults_to_empty_list():
    """__post_init__ sets crisis_indicators to [] when None is passed."""
    ctx = make_agent_context()
    assert ctx.crisis_indicators == []


def test_agent_context_crisis_indicators_explicit_list():
    ctx = make_agent_context(crisis_indicators=["self_harm", "hopelessness"])
    assert "self_harm" in ctx.crisis_indicators


def test_agent_context_with_recent_messages():
    msg = make_message()
    ctx = make_agent_context(recent_messages=[msg])
    assert len(ctx.recent_messages) == 1
    assert ctx.recent_messages[0].content == "Hello"


def test_agent_context_optional_fields_default_none():
    ctx = make_agent_context()
    assert ctx.emotional_state is None
    assert ctx.session_duration is None


def test_agent_context_with_optional_fields():
    ctx = make_agent_context(emotional_state="anxious", session_duration=30)
    assert ctx.emotional_state == "anxious"
    assert ctx.session_duration == 30


# ---------------------------------------------------------------------------
# TherapyResponse
# ---------------------------------------------------------------------------

def test_therapy_response_construction():
    ts = now()
    resp = TherapyResponse(
        message="I understand.",
        agent_type="therapy",
        conversation_id="c1",
        timestamp=ts,
        therapeutic_approach="cognitive",
        emotional_tone="encouraging",
        follow_up_suggestions=["try journaling"],
    )
    assert resp.message == "I understand."
    assert resp.therapeutic_approach == "cognitive"
    assert resp.emotional_tone == "encouraging"
    assert resp.follow_up_suggestions == ["try journaling"]
    assert resp.crisis_detected is False
    assert resp.metadata == {}


def test_therapy_response_crisis_detected_default_false():
    resp = make_therapy_response()
    assert resp.crisis_detected is False


def test_therapy_response_crisis_detected_can_be_set():
    resp = make_therapy_response(crisis_detected=True)
    assert resp.crisis_detected is True


def test_therapy_response_metadata_defaults_to_empty_dict():
    resp = make_therapy_response()
    assert resp.metadata == {}


def test_therapy_response_with_metadata():
    resp = make_therapy_response(metadata={"session_id": "s1", "tokens": 150})
    assert resp.metadata["session_id"] == "s1"


def test_therapy_response_follow_up_suggestions_defaults_empty():
    """__post_init__ converts None follow_up_suggestions to []."""
    resp = make_therapy_response(follow_up_suggestions=None)
    assert resp.follow_up_suggestions == []


def test_therapy_response_with_multiple_suggestions():
    resp = make_therapy_response(follow_up_suggestions=["breathe", "journal", "walk"])
    assert len(resp.follow_up_suggestions) == 3
