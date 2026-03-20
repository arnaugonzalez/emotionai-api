"""Unit tests for SqlAlchemyEventRepository"""
import pytest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.infrastructure.events.repositories.sqlalchemy_event_repository import SqlAlchemyEventRepository
from src.domain.events.domain_events import DomainEvent


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


def _make_domain_event() -> DomainEvent:
    return DomainEvent(
        event_id=str(uuid4()),
        occurred_at=datetime.now(timezone.utc),
        event_type="test_event",
    )


def _make_domain_event_model_mock():
    """Create a mock with DomainEventModel columns."""
    model = MagicMock()
    model.id = uuid4()
    model.event_type = "test_event"
    model.event_data = {"event_id": str(uuid4()), "event_type": "test_event"}
    model.aggregate_id = str(uuid4())
    model.aggregate_type = "test"
    model.user_id = uuid4()
    model.processed = False
    model.processed_at = None
    model.created_at = datetime.now(timezone.utc)
    return model


@pytest.mark.asyncio
async def test_save_event_persists_to_db(mock_db):
    """Verify session.add called with DomainEventModel and flush called."""
    db, mock_session = mock_db

    repo = SqlAlchemyEventRepository(db)
    event = _make_domain_event()

    await repo.save_event(event)

    mock_session.add.assert_called_once()
    mock_session.flush.assert_called_once()


@pytest.mark.asyncio
async def test_get_events_by_user_returns_domain_events(mock_db):
    """Verify ORM rows are mapped back to DomainEvent instances."""
    db, mock_session = mock_db
    user_id = uuid4()
    row = _make_domain_event_model_mock()
    row.user_id = user_id

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row]
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEventRepository(db)
    result = await repo.get_events_by_user(user_id)

    assert len(result) == 1
    assert isinstance(result[0], DomainEvent)
    assert result[0].event_type == row.event_type


@pytest.mark.asyncio
async def test_get_events_by_user_filters_by_event_type(mock_db):
    """When event_types passed, verify query includes type filter."""
    db, mock_session = mock_db
    user_id = uuid4()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEventRepository(db)
    await repo.get_events_by_user(user_id, event_types=["user_created"])

    assert mock_session.execute.called
    call_args = mock_session.execute.call_args[0][0]
    compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
    assert "user_created" in compiled


@pytest.mark.asyncio
async def test_get_unprocessed_events_filters_processed_false(mock_db):
    """Verify query has processed = false filter."""
    db, mock_session = mock_db

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEventRepository(db)
    await repo.get_unprocessed_events()

    assert mock_session.execute.called
    call_args = mock_session.execute.call_args[0][0]
    compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
    assert "processed" in compiled
    assert "false" in compiled.lower() or "False" in compiled


@pytest.mark.asyncio
async def test_mark_event_processed_sets_processed_true_and_timestamp(mock_db):
    """Verify model.processed set to True and processed_at set to a datetime."""
    db, mock_session = mock_db
    event_id = str(uuid4())
    model_mock = _make_domain_event_model_mock()
    model_mock.aggregate_id = event_id

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = model_mock
    mock_session.execute = AsyncMock(return_value=mock_result)

    repo = SqlAlchemyEventRepository(db)
    await repo.mark_event_processed(event_id)

    assert model_mock.processed is True
    assert model_mock.processed_at is not None
    assert isinstance(model_mock.processed_at, datetime)
    mock_session.flush.assert_called_once()
