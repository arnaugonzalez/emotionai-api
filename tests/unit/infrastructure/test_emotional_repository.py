"""Unit tests for SqlAlchemyEmotionalRepository"""
import pytest
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
from uuid import uuid4

from src.infrastructure.records.repositories.sqlalchemy_emotional_repository import SqlAlchemyEmotionalRepository


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


def _make_emotional_record_mock(user_id=None):
    """Create a mock EmotionalRecordModel row."""
    record = MagicMock()
    record.id = uuid4()
    record.user_id = user_id or uuid4()
    record.emotion = "happy"
    record.intensity = 7
    record.triggers = ["exercise"]
    record.notes = "Felt great after a run"
    record.recorded_at = datetime.now(timezone.utc)
    record.tags = ["positive", "physical_activity"]
    record.tag_confidence = 0.85
    record.context_data = {}
    record.created_at = datetime.now(timezone.utc)
    return record


@pytest.mark.asyncio
async def test_get_by_user_id_returns_empty_list_when_no_records(mock_db):
    db, mock_session = mock_db
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEmotionalRepository(db)
    result = await repo.get_by_user_id(uuid4())

    assert result == []


@pytest.mark.asyncio
async def test_get_by_user_id_returns_dicts_with_correct_keys(mock_db):
    db, mock_session = mock_db
    user_id = uuid4()
    row1 = _make_emotional_record_mock(user_id)
    row2 = _make_emotional_record_mock(user_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row1, row2]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEmotionalRepository(db)
    result = await repo.get_by_user_id(user_id)

    assert len(result) == 2
    for item in result:
        assert "id" in item
        assert "emotion" in item
        assert "intensity" in item
        assert "notes" in item
        assert "recorded_at" in item
        assert "tags" in item


@pytest.mark.asyncio
async def test_get_by_user_id_respects_limit(mock_db):
    db, mock_session = mock_db
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEmotionalRepository(db)
    await repo.get_by_user_id(uuid4(), limit=5)

    # Verify that execute was called (query was built and executed)
    assert mock_session.execute.called
    # Verify the query string contains limit logic by checking the compiled query
    call_args = mock_session.execute.call_args[0][0]
    compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
    assert "5" in compiled or "LIMIT" in compiled.upper()


@pytest.mark.asyncio
async def test_get_by_user_id_respects_days_back(mock_db):
    db, mock_session = mock_db
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEmotionalRepository(db)
    await repo.get_by_user_id(uuid4(), days_back=7)

    assert mock_session.execute.called
    call_args = mock_session.execute.call_args[0][0]
    compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
    assert "recorded_at" in compiled


@pytest.mark.asyncio
async def test_save_adds_model_and_flushes(mock_db):
    db, mock_session = mock_db

    repo = SqlAlchemyEmotionalRepository(db)
    record_data = {
        "id": uuid4(),
        "user_id": uuid4(),
        "emotion": "calm",
        "intensity": 5,
        "triggers": [],
        "notes": "Meditation session",
        "recorded_at": datetime.now(timezone.utc),
        "tags": [],
        "tag_confidence": None,
        "context_data": {},
        "created_at": datetime.now(timezone.utc),
    }

    await repo.save(record_data)

    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_save_returns_dict_with_id(mock_db):
    db, mock_session = mock_db

    record_id = uuid4()
    repo = SqlAlchemyEmotionalRepository(db)
    record_data = {
        "id": record_id,
        "user_id": uuid4(),
        "emotion": "calm",
        "intensity": 5,
        "triggers": [],
        "notes": "",
        "recorded_at": datetime.now(timezone.utc),
        "tags": [],
        "tag_confidence": None,
        "context_data": {},
        "created_at": datetime.now(timezone.utc),
    }

    result = await repo.save(record_data)

    assert "id" in result
    assert result["id"] == str(record_id)


@pytest.mark.asyncio
async def test_get_emotional_patterns_returns_structure(mock_db):
    db, mock_session = mock_db
    user_id = uuid4()
    row = _make_emotional_record_mock(user_id)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEmotionalRepository(db)
    result = await repo.get_emotional_patterns(user_id)

    assert "dominant_emotions" in result
    assert "mood_trends" in result
    assert "patterns" in result
    assert isinstance(result["dominant_emotions"], list)
    assert isinstance(result["mood_trends"], dict)
    assert isinstance(result["patterns"], list)
