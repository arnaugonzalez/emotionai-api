"""
Unit tests for ORM model hybrid properties.

Tests the Python-level behavior of hybrid_property descriptors on
EmotionalRecordModel and ConversationModel. No database session is needed —
hybrid properties at the instance level behave like regular Python properties.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.infrastructure.database.models import EmotionalRecordModel, ConversationModel


# ---------------------------------------------------------------------------
# EmotionalRecordModel.intensity_level
# ---------------------------------------------------------------------------

class TestEmotionalRecordIntensityLevel:
    """intensity_level maps 1-3→low, 4-7→medium, 8-10→high."""

    @pytest.mark.parametrize("intensity,expected", [
        (1, "low"),
        (3, "low"),
        (4, "medium"),
        (7, "medium"),
        (8, "high"),
        (10, "high"),
    ])
    def test_intensity_level(self, intensity: int, expected: str) -> None:
        record = EmotionalRecordModel(
            id=uuid4(),
            user_id=uuid4(),
            emotion="happy",
            intensity=intensity,
            recorded_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        assert record.intensity_level == expected


# ---------------------------------------------------------------------------
# ConversationModel.duration_days
# ---------------------------------------------------------------------------

class TestConversationDurationDays:
    """duration_days returns whole days elapsed since created_at."""

    def test_created_five_days_ago(self) -> None:
        conv = ConversationModel(
            id=uuid4(),
            user_id=uuid4(),
            agent_type="therapy",
            title="Test",
            created_at=datetime.now(timezone.utc) - timedelta(days=5),
            last_message_at=datetime.now(timezone.utc),
            is_active=True,
            message_count=0,
        )
        assert conv.duration_days == 5

    def test_created_today(self) -> None:
        conv = ConversationModel(
            id=uuid4(),
            user_id=uuid4(),
            agent_type="therapy",
            title="Test",
            created_at=datetime.now(timezone.utc),
            last_message_at=datetime.now(timezone.utc),
            is_active=True,
            message_count=0,
        )
        assert conv.duration_days == 0
