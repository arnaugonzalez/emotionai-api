# Celery + Redis — EmotionAI study guide

## What is it and why do we use it here

Celery is a Python task queue. It lets the API hand off slow or non-critical work to a separate worker process instead of doing everything inside the HTTP request. Redis plays two roles in this slice:

- broker: stores queued task messages until a worker picks them up
- backend: stores task state and results so Flower can inspect them

In EmotionAI, we use Celery + Redis so `POST /v1/api/emotional_records/` can save the record immediately and then enqueue follow-up work with `notify_new_record.delay(...)`. That separation gives us a cleaner runtime model:

- FastAPI handles request/response work
- Redis buffers background jobs
- Celery workers execute jobs outside the API process
- Flower shows task activity and status

This slice is intentionally small: the task is still a stub notification, but the infrastructure is real and uses the same startup path the roadmap requires.

## How it works conceptually

The mental model is broker -> queue -> worker -> backend.

1. The API calls `.delay()` on a task.
2. Celery serializes the task name and arguments into a Redis message.
3. A Celery worker process, already subscribed to that queue, pulls the message.
4. The worker imports the task function and runs it.
5. Celery stores execution state and result in Redis.
6. Flower reads Celery state and exposes it through its UI and HTTP API.

The worker lifecycle matters:

- the worker must be importable without booting FastAPI
- worker startup must prove a real process can connect to Redis and register tasks
- task execution must happen after database commit if the worker depends on committed data

In this repo, the canonical startup command is:

```bash
celery -A src.infrastructure.tasks.worker worker --loglevel=info
```

That command targets a dedicated worker module instead of the FastAPI app, which keeps worker boot predictable and avoids accidental app startup side effects.

## Key patterns used in this project

### 1. Standalone worker module boundary

`src/infrastructure/tasks/worker.py` creates the Celery app from environment variables only:

```python
import os
from celery import Celery

celery_app = Celery(
    "emotionai",
    broker=os.environ["REDIS_URL"],
    backend=os.environ["REDIS_URL"],
    include=["src.infrastructure.tasks.notification_tasks"],
)

app = celery_app
```

Why this matters:

- Celery workers can import the module without constructing the DI container
- no FastAPI app startup runs during worker boot
- the roadmap command `celery -A src.infrastructure.tasks.worker worker --loglevel=info` stays valid

### 2. `@shared_task` keeps task modules loosely coupled

`src/infrastructure/tasks/notification_tasks.py` uses `@shared_task` instead of binding directly to the app:

```python
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
    logger.info("[notify_new_record] record_id=%s user_id=%s", record_id, user_id)
    return {"status": "notified", "record_id": record_id, "user_id": user_id}
```

This pattern gives us:

- lazy registration through the worker `include` list
- retry and backoff without handwritten retry loops
- a stable task name that Flower can display

### 3. Post-commit dispatch from the records router

The records API commits first, then enqueues:

```python
session.add(model)
await session.commit()
_enqueue_record_notification(str(model.id), str(user_id))
```

That ordering is important. If we queued before commit, the worker could run against data that is not committed yet or might roll back. The helper also swallows broker failures so record creation still succeeds:

```python
def _enqueue_record_notification(record_id: str, user_id: str) -> None:
    try:
        notify_new_record.delay(record_id, user_id)
    except Exception:
        logger.exception(
            "Failed to enqueue notify_new_record task",
            extra={"record_id": record_id, "user_id": user_id},
        )
```

### 4. Redis is both broker and backend in this slice

This repo uses the same `REDIS_URL` for both roles. That keeps local setup small and is enough for a learning slice. It also means Flower can inspect task completion from the same Redis instance the worker is already using.

## Common mistakes and how to avoid them

### Importing the FastAPI app from the worker

Bad outcome: worker boot triggers unrelated startup logic, circular imports, or DB side effects.

Avoid it by keeping `src.infrastructure.tasks.worker` standalone and reading `REDIS_URL` directly from the environment.

### Dispatching before `commit()`

Bad outcome: the worker sees uncommitted or rolled-back state.

Avoid it by enqueueing only after `await session.commit()`.

### Using `async def` task bodies without a bridge

Celery workers are synchronous by default. An `async def` task body does not run the way many people expect unless you explicitly bridge it.

Avoid it by:

- keeping simple tasks synchronous
- using `asyncio.run(...)` inside the task only when async code is truly required later

### Treating broker outages as API outages

If background work is optional for the request, failing the HTTP request because Redis is down is usually the wrong tradeoff.

Avoid it by catching enqueue exceptions in the router helper and logging them. That is exactly what this slice does.

### Verifying only imports, not real worker startup

Import checks do not prove the worker can actually connect to Redis and reach the ready state.

Avoid it by running the real worker command in a smoke script and checking startup logs for a ready signal. This plan adds that executable smoke path.

### Forgetting Flower is part of the runtime chain

Seeing the page load is weaker than verifying the task reached `SUCCESS`.

Avoid it by polling Flower's `/api/tasks` endpoint until `emotionai.notify_new_record` appears as completed.

## Further reading

- Celery docs: https://docs.celeryq.dev/
- Celery routing and tasks guide: https://docs.celeryq.dev/en/stable/userguide/tasks.html
- Redis as Celery broker/backend: https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html
- Flower docs: https://flower.readthedocs.io/
- FastAPI background tasks comparison: https://fastapi.tiangolo.com/tutorial/background-tasks/
