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

## When to use Celery (vs alternatives)

| Scenario | Best tool | Why |
|----------|-----------|-----|
| Fire-and-forget notification after DB commit | Celery + Redis | Decouples slow work from HTTP response; EmotionAI's exact use case. |
| Simple background task with no retry needs | FastAPI `BackgroundTasks` | Zero infrastructure. Good for logging, webhooks with no retry. |
| Job must survive API restart (durability) | Celery + Redis/RabbitMQ | Messages persist in broker. FastAPI BackgroundTasks live only in-process. |
| Scheduled/recurring jobs (cron replacement) | Celery Beat | Built-in periodic task scheduler. |
| Parallel fan-out with result aggregation | Celery canvas (group/chord) | Primitives for running tasks in parallel and collecting results. |
| CPU-bound work (image processing, ML) | Celery + dedicated worker pool | Offloads CPU from the async event loop entirely. |
| Real-time bi-directional messaging | Redis Pub/Sub or WebSocket | Celery is optimized for one-way task dispatch, not request-reply. |

EmotionAI decision: Celery for post-commit background work (notifications, future email sending);
FastAPI BackgroundTasks explicitly avoided because record creation durability requires broker persistence.

## Advanced code examples

### Celery canvas: chaining tasks

When a second task must run only after a first task completes:

```python
from celery import chain
from src.infrastructure.tasks.notification_tasks import notify_new_record

# Hypothetical: notify, then generate weekly summary
result = chain(
    notify_new_record.s(record_id, user_id),
    generate_weekly_summary.s(user_id),
).apply_async()
```

`chain` passes the return value of each task as the first argument to the next.

### Retry with exponential backoff — reading the EmotionAI config

```python
@shared_task(
    bind=True,
    name="emotionai.notify_new_record",
    autoretry_for=(Exception,),
    retry_backoff=True,       # doubles wait: 1s, 2s, 4s, ...
    retry_backoff_max=60,     # caps wait at 60s
    retry_jitter=True,        # adds random offset to prevent thundering herd
    max_retries=3,
    acks_late=True,           # worker acks AFTER completion, not on receipt
)
def notify_new_record(self, record_id: str, user_id: str) -> dict:
    ...
```

`acks_late=True` means the broker message is NOT acknowledged until the task returns. If the
worker crashes mid-execution, the message is redelivered to another worker. Without `acks_late`,
a crash after receipt but before completion silently drops the task.

### Polling Flower API for task completion (used in demo_steps/20_celery.sh)

```bash
# After triggering a task, poll Flower until it shows SUCCESS
for i in $(seq 1 10); do
    result=$(curl -s "http://localhost:5555/api/tasks?limit=1")
    if echo "$result" | grep -q '"state": "SUCCESS"'; then
        echo "Task completed successfully"
        break
    fi
    sleep 2
done
```

The Python equivalent using httpx:

```python
import httpx, asyncio

async def wait_for_task_success(flower_url: str, timeout: int = 20) -> bool:
    async with httpx.AsyncClient() as client:
        for _ in range(timeout // 2):
            resp = await client.get(f"{flower_url}/api/tasks?limit=5")
            tasks = resp.json()
            if any(t.get("state") == "SUCCESS" for t in tasks.values()):
                return True
            await asyncio.sleep(2)
    return False
```

### Running a task synchronously in tests (no broker needed)

```python
from src.infrastructure.tasks.notification_tasks import notify_new_record

def test_notify_new_record_returns_correct_shape():
    result = notify_new_record.apply(args=["record-123", "user-456"]).get()
    assert result["status"] == "notified"
    assert result["record_id"] == "record-123"
```

`task.apply()` runs the task in the current process without a broker. Use this for unit tests.
`task.apply_async()` requires a real broker.

## Interview Prep — Celery + Redis

**Q1: What are the roles of broker and backend in Celery? Can they be the same Redis instance?**

Broker: stores queued task messages until a worker picks them up. Backend: stores task execution
state and results so callers can check whether a task succeeded. They can be the same Redis
instance (as in EmotionAI) for simplicity. In production you may separate them to control
eviction policies independently — broker messages should not be evicted while tasks are queued.

**Q2: Why does EmotionAI use `@shared_task` instead of `@celery_app.task`?**

`@shared_task` does not bind to a specific `Celery` instance at decoration time. The task module
can be imported without first constructing the app. When the worker starts and the `include` list
causes the module to load, `@shared_task` re-binds to the real app. This prevents circular imports
and keeps task modules testable in isolation.

**Q3: Why must the worker module (`worker.py`) not import from the FastAPI app?**

Worker boot must be cheap and predictable. Importing FastAPI app modules would trigger the
dependency injection container build, database pool initialization, and potentially LangChain
agent setup — all of which are wasted work for a worker that only needs Redis connectivity. It
also risks circular imports and slow startup that times out in production. EmotionAI's
`src/infrastructure/tasks/worker.py` reads only `os.environ["REDIS_URL"]`.

**Q4: Why does EmotionAI dispatch the Celery task AFTER `await session.commit()`?**

If the task were dispatched before commit, the worker could execute while the transaction is
still open or has rolled back. The worker reads from the database — it would either see no data
or stale data. The pattern is: write → commit → enqueue, so workers only ever see committed state.

**Q5: What does `acks_late=True` do and why is it important for reliability?**

By default, Celery acknowledges (removes) the broker message as soon as the worker receives it.
If the worker crashes during execution, the task is lost. `acks_late=True` keeps the message in
the broker until the task function returns. If the worker dies mid-execution, the broker
redelivers the message. The tradeoff: with idempotent tasks, redelivery is safe. With
non-idempotent tasks (e.g. sending an email), duplicate execution is possible.

**Q6: How does `autoretry_for=(Exception,)` differ from manual retry inside the task?**

`autoretry_for` catches the specified exception types after the task body raises, then
automatically calls `self.retry()` with the configured backoff. Manual retry requires catching
exceptions yourself, calling `raise self.retry(exc=e, countdown=...)`, and managing backoff
math. `autoretry_for` is cleaner and less error-prone for standard retry patterns.

**Q7: What is Flower and what can it tell you?**

Flower is a real-time web UI and REST API for monitoring Celery. It shows: active workers and
their status, queued and processed tasks, task execution history with state (PENDING, STARTED,
SUCCESS, FAILURE, RETRY), worker resource usage. EmotionAI uses Flower's `/api/tasks` endpoint
in `demo_steps/20_celery.sh` to programmatically assert that `emotionai.notify_new_record`
reached SUCCESS.

**Q8: What is the difference between `delay()` and `apply_async()`?**

`delay(*args, **kwargs)` is shorthand for `apply_async(args, kwargs)` with no additional options.
`apply_async()` exposes all task routing options: `countdown` (delay before execution), `eta`
(scheduled timestamp), `queue` (specific queue name), `priority`, `expires`. Use `delay()` for
simple fire-and-forget; use `apply_async()` when you need routing control.

**Q9: Why is using `async def` in a Celery task body dangerous without a bridge?**

Celery workers run synchronous Python. An `async def` task body defines a coroutine but the
Celery runner calls it as a regular function — it gets a coroutine object back and returns
immediately without running any of the async code. The fix is either: keep tasks synchronous,
or explicitly bridge with `asyncio.run(your_async_fn())` inside the task body. EmotionAI's
`notify_new_record` is synchronous precisely to avoid this.

**Q10: How would you ensure a task is idempotent so retries are safe?**

Design the task so running it multiple times produces the same result. For `notify_new_record`,
idempotency means checking whether a notification was already sent before sending again:
store a `notification_sent_at` timestamp on the record, and skip the send if it is already set.
This makes `acks_late=True` retries safe even if the worker crashes after sending but before
acknowledging.

## Gotchas interviewers test on

**"What happens if you dispatch a task before `session.commit()`?"**
The worker may read no data or stale data. The task runs against the database, and the transaction
from the HTTP handler is still open (or may roll back). EmotionAI explicitly enqueues only after
`await session.commit()`. This is a common gotcha in interviews about task-queue integration with
ORMs.

**"What is the difference between a Celery worker and a Celery beat process?"**
A worker executes tasks from the queue. Beat is a scheduler process that enqueues periodic tasks
on a schedule (like cron). You need both running for scheduled tasks to execute — Beat enqueues,
workers execute. Running only Beat means tasks are queued but never consumed; running only
workers means no periodic tasks are scheduled.

**"Can two Celery workers process the same task simultaneously?"**
Yes, without `acks_late=True`. The default is to ack on receipt. If two workers both pull the
same message before either acks it (possible with certain broker configs), both execute the task.
With `acks_late=True`, the message stays in the queue until one worker finishes; Redis handles
atomic message delivery so only one worker gets each message.

**"What does `bind=True` on a `@shared_task` do?"**
It makes the first argument to the task function the task instance itself (`self`). Without
`bind=True`, you cannot call `self.retry()`, access `self.request.id` (the task UUID), or read
retry counts with `self.request.retries`. EmotionAI's `notify_new_record` uses `bind=True` to
support `self.retry()` via `autoretry_for`.

**"How does swallowing enqueue exceptions affect observability?"**
EmotionAI logs broker failures in `_enqueue_record_notification()` but does not surface them to
the caller. This means a Redis outage is invisible at the HTTP level — records appear to create
successfully. The operational implication: you need log-based alerting on
`"Failed to enqueue notify_new_record task"` to detect silent task loss. Without that alert,
Redis being down is undetectable from API response codes alone.
