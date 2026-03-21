"""Unit tests for SqlAlchemyAnalyticsRepository"""
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4


@pytest.mark.asyncio
async def test_save_agent_interaction_logs_structured_data():
    """Verify logger.info is called with user_id, agent_type, interaction_data keys."""
    with patch(
        "src.infrastructure.analytics.repositories.sqlalchemy_analytics_repository.logger"
    ) as mock_logger:
        from src.infrastructure.analytics.repositories.sqlalchemy_analytics_repository import (
            SqlAlchemyAnalyticsRepository,
        )

        db = MagicMock()
        repo = SqlAlchemyAnalyticsRepository(db)
        user_id = uuid4()
        agent_type = "therapy_agent"
        interaction_data = {"message": "hello", "response": "hi"}

        await repo.save_agent_interaction(user_id, agent_type, interaction_data)

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        # First positional arg is the message
        assert call_args[0][0] == "agent_interaction"
        # extra kwarg contains the structured fields
        extra = call_args[1]["extra"]
        assert "user_id" in extra
        assert extra["user_id"] == str(user_id)
        assert "agent_type" in extra
        assert extra["agent_type"] == agent_type
        assert "interaction_data" in extra


@pytest.mark.asyncio
async def test_save_agent_interaction_returns_none():
    """Verify return value is None."""
    with patch(
        "src.infrastructure.analytics.repositories.sqlalchemy_analytics_repository.logger"
    ):
        from src.infrastructure.analytics.repositories.sqlalchemy_analytics_repository import (
            SqlAlchemyAnalyticsRepository,
        )

        db = MagicMock()
        repo = SqlAlchemyAnalyticsRepository(db)

        result = await repo.save_agent_interaction(uuid4(), "agent", {})

        assert result is None
