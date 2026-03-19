"""
Tests for AgentChatUseCase.

Strategy: inject AsyncMock for every interface dependency.
The use case coordinates many services; tests verify:
  - Happy-path delegation to agent_service.send_message
  - Crisis detection passthrough (response attribute preserved)
  - Exception propagation when agent_service fails
  - Token usage logging when response carries metadata
  - Token logging is skipped gracefully when token_usage_repo is None
  - Correct argument forwarding (user_id, agent_type, message, context)
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.application.chat.use_cases.agent_chat_use_case import AgentChatUseCase

USER_ID = UUID("aaaabbbb-cccc-dddd-eeee-ffffaaaabbbb")


def make_use_case(**kwargs) -> AgentChatUseCase:
    """
    Build an AgentChatUseCase with all dependencies mocked.

    Pass keyword overrides to replace specific mocks (e.g. agent_service=my_mock).
    database and token_usage_repo default to None so suggestion/token paths are skipped.
    """
    defaults = dict(
        user_repository=AsyncMock(),
        emotional_repository=AsyncMock(),
        breathing_repository=AsyncMock(),
        conversation_repository=AsyncMock(),
        event_repository=AsyncMock(),
        agent_service=AsyncMock(),
        tagging_service=AsyncMock(),
        user_knowledge_service=AsyncMock(),
        similarity_search_service=AsyncMock(),
        database=None,
        token_usage_repo=None,
    )
    defaults.update(kwargs)
    return AgentChatUseCase(**defaults)


def make_response(**kwargs) -> MagicMock:
    """Return a mock TherapyResponse with sensible defaults."""
    resp = MagicMock()
    resp.crisis_detected = kwargs.get("crisis_detected", False)
    resp.metadata = kwargs.get("metadata", {})
    resp.follow_up_suggestions = kwargs.get("follow_up_suggestions", [])
    resp.conversation_id = kwargs.get("conversation_id", str(uuid4()))
    return resp


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_chat_returns_response_from_agent_service() -> None:
    """Use case returns whatever agent_service.send_message returns."""
    expected = make_response()
    use_case = make_use_case(agent_service=AsyncMock(send_message=AsyncMock(return_value=expected)))

    result = await use_case.execute(
        user_id=USER_ID,
        agent_type="therapist",
        message="Hello",
    )

    assert result is expected


async def test_chat_passes_correct_args_to_agent_service() -> None:
    """execute() must forward user_id, agent_type, message, and context to agent_service."""
    mock_agent = AsyncMock()
    mock_agent.send_message.return_value = make_response()
    use_case = make_use_case(agent_service=mock_agent)

    context = {"session_id": "xyz"}
    await use_case.execute(
        user_id=USER_ID,
        agent_type="coach",
        message="I feel anxious",
        context=context,
    )

    mock_agent.send_message.assert_called_once_with(USER_ID, "coach", "I feel anxious", context)


async def test_chat_passes_empty_dict_when_context_is_none() -> None:
    """When context=None, the use case passes {} (not None) to agent_service."""
    mock_agent = AsyncMock()
    mock_agent.send_message.return_value = make_response()
    use_case = make_use_case(agent_service=mock_agent)

    await use_case.execute(user_id=USER_ID, agent_type="therapist", message="Hi")

    _, _, _, ctx = mock_agent.send_message.call_args.args
    assert ctx == {}


# ---------------------------------------------------------------------------
# Crisis detection passthrough
# ---------------------------------------------------------------------------


async def test_chat_preserves_crisis_detected_true_on_response() -> None:
    """Use case must not strip or modify crisis_detected on the response object."""
    crisis_response = make_response(crisis_detected=True)
    use_case = make_use_case(
        agent_service=AsyncMock(send_message=AsyncMock(return_value=crisis_response))
    )

    result = await use_case.execute(user_id=USER_ID, agent_type="therapist", message="I want to hurt myself")

    assert result.crisis_detected is True


async def test_chat_preserves_crisis_detected_false_on_normal_response() -> None:
    """crisis_detected=False must also pass through unchanged."""
    normal_response = make_response(crisis_detected=False)
    use_case = make_use_case(
        agent_service=AsyncMock(send_message=AsyncMock(return_value=normal_response))
    )

    result = await use_case.execute(user_id=USER_ID, agent_type="therapist", message="How are you?")

    assert result.crisis_detected is False


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


async def test_chat_raises_when_agent_service_raises() -> None:
    """If agent_service.send_message raises, the use case re-raises the same exception."""
    mock_agent = AsyncMock()
    mock_agent.send_message.side_effect = RuntimeError("OpenAI timeout")
    use_case = make_use_case(agent_service=mock_agent)

    with pytest.raises(RuntimeError, match="OpenAI timeout"):
        await use_case.execute(user_id=USER_ID, agent_type="therapist", message="Hi")


async def test_chat_raises_attribute_error_when_send_message_missing() -> None:
    """If agent_service lacks send_message, use case raises AttributeError explicitly."""
    bad_service = MagicMock(spec=[])  # no attributes
    use_case = make_use_case(agent_service=bad_service)

    with pytest.raises(AttributeError, match="send_message"):
        await use_case.execute(user_id=USER_ID, agent_type="therapist", message="Hi")


# ---------------------------------------------------------------------------
# Token usage logging (best-effort)
# ---------------------------------------------------------------------------


async def test_chat_logs_token_usage_when_metadata_present() -> None:
    """Token usage is logged via token_usage_repo when metadata carries usage data."""
    token_repo = AsyncMock()
    usage_data = {"tokens_total": 300, "tokens_prompt": 200, "tokens_completion": 100}
    response = make_response(metadata={"llm_model": "gpt-4o-mini", "usage": usage_data})
    mock_agent = AsyncMock(send_message=AsyncMock(return_value=response))

    use_case = make_use_case(agent_service=mock_agent, token_usage_repo=token_repo)
    await use_case.execute(user_id=USER_ID, agent_type="therapist", message="Hello")

    token_repo.log_usage.assert_called_once()
    call_kwargs = token_repo.log_usage.call_args.kwargs
    assert call_kwargs["user_id"] == USER_ID
    assert call_kwargs["total_tokens"] == 300
    assert call_kwargs["tokens_prompt"] == 200
    assert call_kwargs["tokens_completion"] == 100
    assert call_kwargs["model"] == "gpt-4o-mini"


async def test_chat_skips_token_logging_when_token_usage_repo_is_none() -> None:
    """No crash and no logging when token_usage_repo is None (feature flag off)."""
    usage_data = {"tokens_total": 500, "tokens_prompt": 300, "tokens_completion": 200}
    response = make_response(metadata={"usage": usage_data})
    mock_agent = AsyncMock(send_message=AsyncMock(return_value=response))

    # token_usage_repo defaults to None in make_use_case
    use_case = make_use_case(agent_service=mock_agent)

    # Must not raise
    result = await use_case.execute(user_id=USER_ID, agent_type="therapist", message="Hello")
    assert result is response


async def test_chat_skips_token_logging_when_token_total_is_zero() -> None:
    """Token logging is skipped when tokens_total == 0 even if repo is provided."""
    token_repo = AsyncMock()
    usage_data = {"tokens_total": 0, "tokens_prompt": 0, "tokens_completion": 0}
    response = make_response(metadata={"usage": usage_data})
    mock_agent = AsyncMock(send_message=AsyncMock(return_value=response))

    use_case = make_use_case(agent_service=mock_agent, token_usage_repo=token_repo)
    await use_case.execute(user_id=USER_ID, agent_type="therapist", message="Hello")

    token_repo.log_usage.assert_not_called()


async def test_chat_token_logging_failure_does_not_abort_response() -> None:
    """A crash in token logging must not prevent the response from being returned."""
    token_repo = AsyncMock()
    token_repo.log_usage.side_effect = Exception("logging DB down")
    usage_data = {"tokens_total": 100, "tokens_prompt": 60, "tokens_completion": 40}
    response = make_response(metadata={"usage": usage_data})
    mock_agent = AsyncMock(send_message=AsyncMock(return_value=response))

    use_case = make_use_case(agent_service=mock_agent, token_usage_repo=token_repo)
    result = await use_case.execute(user_id=USER_ID, agent_type="therapist", message="Hello")

    assert result is response
