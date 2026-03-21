"""Unit tests for SqlAlchemyBreathingRepository"""
import pytest
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.infrastructure.breathing.repositories.sqlalchemy_breathing_repository import SqlAlchemyBreathingRepository


@pytest.fixture()
def mock_db():
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    db = MagicMock()

    @asynccontextmanager
    async def _get_session():
        yield mock_session

    db.get_session = _get_session
    return db, mock_session


def _make_breathing_session_mock(user_id=None):
    """Create a mock BreathingSessionModel row."""
    session = MagicMock()
    session.id = uuid4()
    session.user_id = user_id or uuid4()
    session.pattern_name = "4-7-8"
    session.duration_minutes = 10
    session.completed = True
    session.effectiveness_rating = 4
    session.notes = "Felt relaxed"
    session.started_at = datetime.now(timezone.utc)
    session.completed_at = datetime.now(timezone.utc)
    session.tags = ["relaxation"]
    session.tag_confidence = 0.9
    session.session_data = {}
    return session


@pytest.mark.asyncio
async def test_get_by_user_id_returns_empty_list(mock_db):
    db, mock_session = mock_db
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyBreathingRepository(db)
    result = await repo.get_by_user_id(uuid4())

    assert result == []


@pytest.mark.asyncio
async def test_get_by_user_id_returns_dicts(mock_db):
    db, mock_session = mock_db
    user_id = uuid4()
    row1 = _make_breathing_session_mock(user_id)
    row2 = _make_breathing_session_mock(user_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row1, row2]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyBreathingRepository(db)
    result = await repo.get_by_user_id(user_id)

    assert len(result) == 2
    for item in result:
        assert "id" in item
        assert "pattern_name" in item
        assert "duration_minutes" in item
        assert "completed" in item
        assert "effectiveness_rating" in item
        assert "started_at" in item


@pytest.mark.asyncio
async def test_save_adds_model_and_flushes(mock_db):
    db, mock_session = mock_db

    repo = SqlAlchemyBreathingRepository(db)
    session_data = {
        "id": uuid4(),
        "user_id": uuid4(),
        "pattern_name": "box-breathing",
        "duration_minutes": 5,
        "completed": True,
        "effectiveness_rating": 3,
        "notes": "",
        "started_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
        "tags": [],
        "tag_confidence": None,
        "session_data": {},
    }

    await repo.save(session_data)

    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_save_returns_dict_with_id(mock_db):
    db, mock_session = mock_db

    session_id = uuid4()
    repo = SqlAlchemyBreathingRepository(db)
    session_data = {
        "id": session_id,
        "user_id": uuid4(),
        "pattern_name": "box-breathing",
        "duration_minutes": 5,
        "completed": False,
        "effectiveness_rating": None,
        "notes": "",
        "started_at": datetime.now(timezone.utc),
        "completed_at": None,
        "tags": [],
        "tag_confidence": None,
        "session_data": {},
    }

    result = await repo.save(session_data)

    assert "id" in result
    assert result["id"] == str(session_id)


@pytest.mark.asyncio
async def test_get_session_analytics_returns_structure(mock_db):
    db, mock_session = mock_db
    user_id = uuid4()
    row1 = _make_breathing_session_mock(user_id)
    row2 = _make_breathing_session_mock(user_id)
    row2.pattern_name = "diaphragmatic"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row1, row2]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyBreathingRepository(db)
    result = await repo.get_session_analytics(user_id)

    assert "total_sessions" in result
    assert "average_duration" in result
    assert "improvement_trend" in result
    assert "favorite_patterns" in result
    assert result["total_sessions"] == 2
    assert isinstance(result["favorite_patterns"], list)
