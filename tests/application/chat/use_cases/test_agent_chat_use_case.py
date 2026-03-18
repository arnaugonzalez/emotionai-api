from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.chat.use_cases.agent_chat_use_case import AgentChatUseCase


def _build_use_case(agent_service, token_usage_repo=None):
    return AgentChatUseCase(
        user_repository=MagicMock(),
        emotional_repository=MagicMock(),
        breathing_repository=MagicMock(),
        conversation_repository=MagicMock(),
        event_repository=MagicMock(),
        agent_service=agent_service,
        tagging_service=MagicMock(),
        user_knowledge_service=MagicMock(),
        similarity_search_service=MagicMock(),
        database=None,
        token_usage_repo=token_usage_repo,
    )


@pytest.mark.asyncio
async def test_execute_returns_response_and_calls_agent_service():
    response = SimpleNamespace(metadata={})
    agent_service = MagicMock()
    agent_service.send_message = AsyncMock(return_value=response)

    use_case = _build_use_case(agent_service=agent_service)
    user_id = uuid4()

    result = await use_case.execute(user_id=user_id, agent_type="coach", message="Hello")

    assert result is response
    agent_service.send_message.assert_awaited_once_with(user_id, "coach", "Hello", {})


@pytest.mark.asyncio
async def test_execute_raises_when_agent_service_has_no_send_message():
    agent_service = object()  # does not implement send_message
    use_case = _build_use_case(agent_service=agent_service)

    with pytest.raises(AttributeError):
        await use_case.execute(user_id=uuid4(), agent_type="coach", message="Hi")


@pytest.mark.asyncio
async def test_execute_logs_token_usage_when_usage_metadata_present():
    response = SimpleNamespace(
        metadata={
            "llm_model": "gpt-4o-mini",
            "usage": {
                "tokens_total": 42,
                "tokens_prompt": 30,
                "tokens_completion": 12,
            },
        },
        conversation_id="conv-1",
        follow_up_suggestions=[],
    )
    agent_service = MagicMock()
    agent_service.send_message = AsyncMock(return_value=response)
    token_usage_repo = MagicMock()
    token_usage_repo.log_usage = AsyncMock()

    use_case = _build_use_case(agent_service=agent_service, token_usage_repo=token_usage_repo)
    user_id = uuid4()

    result = await use_case.execute(user_id=user_id, agent_type="coach", message="Hello")

    assert result is response
    token_usage_repo.log_usage.assert_awaited_once()
    kwargs = token_usage_repo.log_usage.await_args.kwargs
    assert kwargs["user_id"] == user_id
    assert kwargs["interaction_type"] == "chat"
    assert kwargs["total_tokens"] == 42
    assert kwargs["tokens_prompt"] == 30
    assert kwargs["tokens_completion"] == 12
    assert kwargs["model"] == "gpt-4o-mini"
    assert kwargs["metadata"]["agent_type"] == "coach"


@pytest.mark.asyncio
async def test_execute_does_not_fail_if_token_logging_raises():
    response = SimpleNamespace(
        metadata={"usage": {"tokens_total": 10, "tokens_prompt": 4, "tokens_completion": 6}},
        conversation_id="conv-2",
        follow_up_suggestions=[],
    )
    agent_service = MagicMock()
    agent_service.send_message = AsyncMock(return_value=response)
    token_usage_repo = MagicMock()
    token_usage_repo.log_usage = AsyncMock(side_effect=RuntimeError("logging failed"))

    use_case = _build_use_case(agent_service=agent_service, token_usage_repo=token_usage_repo)

    result = await use_case.execute(user_id=uuid4(), agent_type="coach", message="Hello")
    assert result is response
