from datetime import datetime, timezone
from uuid import uuid4

from src.domain.chat.entities import Message, Conversation, AgentContext, TherapyResponse


def test_agent_context_defaults_crisis_indicators_to_empty_list():
    ctx = AgentContext(
        user_id=uuid4(),
        agent_type="therapy",
        conversation_id="c1",
        recent_messages=[],
        user_profile={"name": "Ana"},
        crisis_indicators=None,
    )
    assert ctx.crisis_indicators == []


def test_therapy_response_defaults_metadata_and_follow_up_suggestions():
    resp = TherapyResponse(
        message="Hi",
        agent_type="therapy",
        conversation_id="c1",
        timestamp=datetime.now(timezone.utc),
        therapeutic_approach="supportive",
        emotional_tone="empathetic",
        follow_up_suggestions=None,
        metadata=None,
    )
    assert resp.metadata == {}
    assert resp.follow_up_suggestions == []


def test_message_and_conversation_simple_fields():
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    m = Message(
        id="m1",
        conversation_id="c1",
        user_id=user_id,
        content="hello",
        message_type="user",
        metadata={"a": 1},
        timestamp=now,
    )
    c = Conversation(
        id="c1",
        user_id=user_id,
        agent_type="therapy",
        title="session",
        created_at=now,
        last_message_at=now,
        message_count=1,
        is_active=True,
    )

    assert m.message_type == "user"
    assert c.message_count == 1
