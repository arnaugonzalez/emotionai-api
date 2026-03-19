"""
Unit tests for src/infrastructure/tasks/notification_tasks.py

Uses .run() to call the task body directly without going through the broker.
This tests the task logic, not the Celery dispatch mechanism.
Dispatch from the router is covered in plan 02 (test_task_dispatch.py).
"""

from src.infrastructure.tasks.notification_tasks import notify_new_record


def test_notify_new_record_returns_notified_status():
    """Task body returns status=notified for any valid record_id/user_id."""
    result = notify_new_record.run("test-record-id", "test-user-id")
    assert result["status"] == "notified"


def test_notify_new_record_echoes_record_id():
    """Task body echoes back the record_id passed as the first argument."""
    result = notify_new_record.run("r2", "u2")
    assert result["record_id"] == "r2"


def test_notify_new_record_echoes_user_id():
    """Task body echoes back the user_id passed as the second argument."""
    result = notify_new_record.run("r3", "u3")
    assert result["user_id"] == "u3"
