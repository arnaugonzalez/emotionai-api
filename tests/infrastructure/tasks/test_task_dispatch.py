import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from src.presentation.api.routers import records


def test_enqueue_record_notification_dispatches_task(monkeypatch):
    calls = []

    def fake_delay(record_id, user_id):
        calls.append((record_id, user_id))

    monkeypatch.setattr(records.notify_new_record, "delay", fake_delay)

    records._enqueue_record_notification("r-1", "u-1")

    assert calls == [("r-1", "u-1")]


def test_enqueue_record_notification_does_not_raise_when_delay_fails(monkeypatch):
    def boom(record_id, user_id):
        raise RuntimeError("broker unavailable")

    monkeypatch.setattr(records.notify_new_record, "delay", boom)

    records._enqueue_record_notification("r-1", "u-1")


def test_dispatch_happens_after_commit_order(monkeypatch):
    user_id = uuid4()
    call_order = []

    class FakeResult:
        def scalar_one_or_none(self):
            return SimpleNamespace(id=user_id)

    class FakeSession:
        def add(self, model):
            return None

        async def execute(self, statement):
            return FakeResult()

        async def commit(self):
            call_order.append("commit")

    session = FakeSession()

    @asynccontextmanager
    async def fake_get_session():
        yield session

    container = SimpleNamespace(database=SimpleNamespace(get_session=fake_get_session))

    monkeypatch.setattr(records, "_check_duplicate_record", AsyncMock(return_value=False))
    monkeypatch.setattr(records, "broadcast_calendar_event", AsyncMock())
    monkeypatch.setattr(
        records,
        "_enqueue_record_notification",
        lambda record_id, current_user_id: call_order.append(
            f"enqueue:{record_id}:{current_user_id}"
        ),
    )

    result = asyncio.run(
        records.create_emotional_record(
            {"emotion": "joy", "intensity": 7, "description": "steady"},
            user_id=user_id,
            container=container,
        )
    )

    assert call_order[0] == "commit"
    assert call_order[1].startswith("enqueue:")
    assert result["status"] == "saved"
