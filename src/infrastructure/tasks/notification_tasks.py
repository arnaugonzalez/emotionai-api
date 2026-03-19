"""
Celery notification tasks for EmotionAI.

Uses @shared_task (not @celery_app.task) to avoid importing the app instance here.
Celery registers these via worker.py's include= config.

Task body is synchronous (def, not async def).
Reason: Celery workers run tasks in a sync prefork pool. An async def body returns
a coroutine object and exits immediately without executing — looks like SUCCESS but
nothing happened. If future tasks need asyncpg, wrap with asyncio.run(_async_fn()).
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="emotionai.notify_new_record",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
)
def notify_new_record(self, record_id: str, user_id: str) -> dict:
    """
    Stub notification task — fired after a new emotional record is saved to DB.

    Demonstrates:
    - Celery task anatomy: broker -> queue -> worker -> backend
    - Retry with exponential backoff and jitter
    - Idempotency: called with record_id, same result if called twice

    Future (Milestone 3): replace logger.info with real notification dispatch
    (push notification, email, or webhook). Move OpenAI tagging here too.
    """
    logger.info("[notify_new_record] record_id=%s user_id=%s", record_id, user_id)
    return {"status": "notified", "record_id": record_id, "user_id": user_id}
