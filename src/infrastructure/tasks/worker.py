"""
Celery application singleton for EmotionAI.

IMPORTANT: This module MUST remain importable without starting the FastAPI app.
- Read REDIS_URL directly from os.environ — never import from container.py.
- No imports from src.presentation, src.application, or src.infrastructure.container.
- No async code at module level — Celery workers are synchronous processes.
"""

import os

from celery import Celery

celery_app = Celery(
    "emotionai",
    broker=os.environ["REDIS_URL"],
    backend=os.environ["REDIS_URL"],
    include=["src.infrastructure.tasks.notification_tasks"],
)

# Roadmap command compatibility: `celery -A src.infrastructure.tasks.worker worker --loglevel=info`
app = celery_app

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=86400,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_send_task_events=True,
    task_send_sent_event=True,
    task_track_started=True,
)
