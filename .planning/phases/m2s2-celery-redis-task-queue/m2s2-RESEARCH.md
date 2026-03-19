# Phase m2s2: Celery + Redis Task Queue — Research

**Researched:** 2026-03-19
**Domain:** Celery 5.x, Redis as broker/backend, FastAPI async integration, Flower monitoring
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Redis is already in docker-compose and requirements — use it as both broker AND backend
- Task module lives in `src/infrastructure/` (infrastructure concern, not application logic)
- Task function must be importable without starting the full FastAPI app
- Best hook point: `POST /v1/api/emotional_records` — after saving a record, fire `notify_new_record.delay(record_id, user_id)`
- The tagging pipeline (OpenAITaggingService) is identified as a perfect async candidate but OUT OF SCOPE for this slice (stub only)
- Flower at localhost:5555 for task monitoring
- Task result stored in Redis with 24h expiry

### Claude's Discretion
- Exact Celery configuration (concurrency, prefetch, task serializer)
- Whether to use `shared_task` decorator or explicit app binding
- Task retry policy for the notification stub (exponential backoff is good practice)
- Flower authentication (none for local dev)

### Deferred Ideas (OUT OF SCOPE)
- Moving tagging pipeline to async (scope creep — stub only this slice)
- Dead letter queues / DLX routing
- Celery Beat for periodic tasks
- Task result persistence to PostgreSQL
</user_constraints>

---

## Summary

Celery 5.x with Redis as broker and backend is the correct choice for this slice. It is the de-facto standard for Python background task processing, has excellent documentation, and the mental model it teaches (broker → queue → worker → backend) maps directly to production patterns. The key learning tension is that Celery workers are fundamentally synchronous processes while EmotionAI's application layer is fully async (asyncpg, FastAPI). For this slice — a simple notification stub — this tension is trivial to resolve: write the Celery task as a plain synchronous function. No asyncio.run() is needed for a stub that just logs or prints.

The `POST /v1/api/emotional_records` router is the correct hook point. After `session.commit()`, add `notify_new_record.delay(str(model.id), str(user_id))` — one line, no change to the response contract. The Celery app instance lives in `src/infrastructure/tasks/worker.py` and is importable standalone because it reads the Redis URL from the environment, not from ApplicationContainer. This avoids circular imports with the FastAPI app.

**Primary recommendation:** Use Celery 5.x with `@shared_task(bind=True)`, Redis as broker+backend, and `asyncio.run()` only if the task body ever needs to call async code. For the notification stub in this slice, keep the task fully synchronous — it is the simplest correct solution and best illustrates the mental model.

---

## Technology Comparison: Where Is More Dev-Friendly?

| Option | Async-native | Separate worker process | Retry/backoff | Monitoring UI | Verdict |
|--------|-------------|------------------------|---------------|---------------|---------|
| **FastAPI BackgroundTasks** | Yes (shares event loop) | No — same uvicorn process | No | No | Too fragile for production. Tasks lost on crash. Blocks the event loop under load. Use only for fire-and-forget in-process work with no retry needs. |
| **ARQ** | Yes (native asyncio) | Yes | Yes | No built-in GUI | Great fit for async codebase but lacks Flower. Smaller ecosystem. Harder to demonstrate in portfolio. |
| **RQ (Redis Queue)** | No | Yes | Limited | Built-in dashboard | Simpler than Celery but less feature-complete. Less industry prevalence. |
| **Celery 5.x** | No (sync workers by default) | Yes | Excellent (autoretry_for, retry_backoff, jitter) | Flower (excellent) | Industry standard. Best for portfolio. Best documentation. Flower is first-class. |

**Recommendation: Celery.** The sync-worker limitation is a non-issue for this slice (stub task). The learning value of Celery's mental model, the Flower UI, and its industry prevalence outweigh ARQ's asyncio purity for this project's goals.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `celery` | `>=5.3,<6` | Task queue framework | Industry standard, 5.x supports Python 3.11+ fully |
| `redis` | already in requirements (`>=5.0.1`) | Broker + result backend | Already deployed, dual-purpose saves infra cost |
| `flower` | `>=2.0` | Real-time task monitoring web UI | Ships with Celery ecosystem, zero config needed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `celery[redis]` | included in celery | Redis transport extras | Always — install as `celery[redis]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Celery | ARQ | ARQ is asyncio-native (better fit for async codebase long-term) but no Flower, smaller community, less portfolio value |
| Celery | FastAPI BackgroundTasks | BackgroundTasks runs in the same process — no worker isolation, no retry, tasks lost on crash. Acceptable only for trivial non-critical work |
| Redis backend | PostgreSQL backend | Simpler but adds dependency; Redis already present; results don't need permanent storage |

**Installation:**
```bash
pip install "celery[redis]>=5.3,<6" "flower>=2.0"
```

Both go in `requirements.txt` (dev) and `requirements-production.txt` (prod).

---

## Architecture Patterns

### Recommended Package Structure
```
src/infrastructure/tasks/
├── __init__.py          # empty — makes it a package
├── worker.py            # Celery app instance (ONLY thing imported by workers)
└── notification_tasks.py  # @shared_task definitions
```

**Why this structure:** `worker.py` must be importable without pulling in the full FastAPI app or ApplicationContainer. It reads settings directly from environment variables. `notification_tasks.py` imports only from `worker.py`. The router imports only from `notification_tasks.py`.

**Importability rule:** Celery worker process runs `celery -A src.infrastructure.tasks.worker worker`. This import path must resolve without triggering FastAPI startup, database connections, or OpenAI client initialization.

### Pattern 1: Celery App Definition (worker.py)
**What:** Single module that creates the Celery app instance. All config lives here.
**When to use:** Always — one app instance per project.

```python
# src/infrastructure/tasks/worker.py
import os
from celery import Celery

celery_app = Celery(
    "emotionai",
    broker=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    include=["src.infrastructure.tasks.notification_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=86400,  # 24 hours — matches CONTEXT.md decision
    worker_prefetch_multiplier=1,  # fair dispatch for heterogeneous tasks
    task_acks_late=True,  # acknowledge AFTER completion, not at receipt
)
```

Note: `REDIS_URL` is already set in docker-compose.yml as `redis://redis:6379`. The Celery worker service will inherit this env var.

### Pattern 2: Shared Task with Retry (notification_tasks.py)
**What:** `@shared_task` does not require importing the app instance — it binds lazily.
**When to use:** Always for tasks in a standalone module.

```python
# src/infrastructure/tasks/notification_tasks.py
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="emotionai.notify_new_record",
    autoretry_for=(Exception,),
    retry_backoff=True,        # exponential: 1s, 2s, 4s, 8s...
    retry_backoff_max=60,      # cap at 60s between retries
    retry_jitter=True,         # randomize to prevent thundering herd
    max_retries=3,
    acks_late=True,
)
def notify_new_record(self, record_id: str, user_id: str) -> dict:
    """
    Stub notification task fired after a new emotional record is saved.

    This is a learning stub demonstrating:
    - Celery task anatomy (broker → queue → worker → backend)
    - Retry with exponential backoff
    - Idempotency: called with record_id — same result if called twice

    Future: replace logger.info with real notification dispatch.
    """
    logger.info(
        f"[notify_new_record] Triggered for record_id={record_id}, user_id={user_id}"
    )
    # Stub: in production, send push notification, email, or webhook here
    return {"status": "notified", "record_id": record_id, "user_id": user_id}
```

**Why `bind=True`:** Gives access to `self.retry()` and `self.request.id` (task ID for logging/idempotency checks). Required when using manual retry patterns or inspecting task context.

**Why `shared_task` not `@celery_app.task`:** `shared_task` avoids importing the app instance into task modules — cleaner separation of concerns. The Celery app registers it via `include=["src.infrastructure.tasks.notification_tasks"]` in `worker.py`.

### Pattern 3: Firing the Task from the Router
**What:** After `session.commit()`, dispatch the task without awaiting it.
**When to use:** After any write that should trigger downstream processing.

```python
# In src/presentation/api/routers/records.py
# Add this import at the top:
from ....infrastructure.tasks.notification_tasks import notify_new_record

# After session.commit() in create_emotional_record:
await session.commit()
notify_new_record.delay(str(model.id), str(user_id))  # fire-and-forget
```

`.delay()` is non-blocking. It publishes a message to Redis and returns immediately. The HTTP response is not delayed. `.delay(arg1, arg2)` is equivalent to `.apply_async(args=[arg1, arg2])` — use `.delay()` for the simple case.

### Pattern 4: Registering Celery in ApplicationContainer
**What:** Store the Celery app in the container for health checks and future injection.
**When to use:** Enables `container.celery_app` access from routers if needed.

```python
# In ApplicationContainer dataclass:
celery_app: Any  # from celery import Celery

# In ApplicationContainer.create():
from .tasks.worker import celery_app
container = cls(
    ...
    celery_app=celery_app,
)
```

The Celery app is a global singleton (already initialized when `worker.py` is imported) — the container just holds a reference. No async initialization needed.

### Anti-Patterns to Avoid
- **Awaiting the task dispatch:** `.delay()` is synchronous (submits to Redis synchronously). Do not wrap it in `await`. The redis-py client used by Celery's broker transport is sync.
- **Importing ApplicationContainer in worker.py:** This triggers database pool initialization inside the worker process — wrong. Worker.py must be standalone.
- **Defining async task functions without asyncio.run():** Celery workers run tasks in a sync thread pool. `async def` task bodies are never awaited by Celery. If you need async in a task body (future slice), wrap with `asyncio.run(your_async_fn(...))`.
- **Using the same Redis DB index for everything:** Celery uses DB 0 by default. The existing RedisEventBus in the codebase also uses the URL without a DB index (defaults to 0). For this slice this is fine; in production, consider using DB 1 for Celery (`redis://redis:6379/1`) to avoid key collisions.

---

## The Async/Sync Tension: Celery + asyncpg

This is the most important technical concept for the planner to document in the learning guide.

### Why This Matters for EmotionAI
EmotionAI is fully async: asyncpg, FastAPI, SQLAlchemy async. Celery workers are synchronous OS processes. They run in a separate process (not the uvicorn process), with their own Python interpreter and no event loop running.

### For This Slice (Stub Task): No Problem
The notification stub task does not call asyncpg or any async code. It logs and returns. Keeping it synchronous is correct and simple.

### For Future Slices (e.g., tagging pipeline as Celery task)
If a task needs to call asyncpg, there are two correct patterns:

**Option A (recommended for occasional async):** `asyncio.run()` inside the sync task body.
```python
@shared_task(bind=True)
def tag_emotional_record(self, record_id: str):
    import asyncio
    result = asyncio.run(_async_tag(record_id))
    return result

async def _async_tag(record_id: str):
    # async code here — gets its own event loop per task invocation
    pass
```
`asyncio.run()` creates a fresh event loop for each task call. No loop reuse issues.

**Option B (for heavy async workloads): use ARQ instead of Celery.** ARQ is asyncio-native and would be the correct long-term choice if the majority of tasks require async. This is deferred per CONTEXT.md.

**Do NOT use:** `asyncio.get_event_loop().run_until_complete()` — deprecated in Python 3.10+ and raises `DeprecationWarning`; can fail if a loop is already running in the process.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Task retry with backoff | Manual retry loop with `time.sleep()` | `autoretry_for + retry_backoff + retry_jitter` on `@shared_task` | Celery handles exponential backoff, jitter, max retries, and max delay cap natively |
| Task status tracking | Custom Redis keys | `AsyncResult(task_id).status` via Celery's result backend | Thread-safe, standard states: PENDING/STARTED/SUCCESS/FAILURE/RETRY |
| Worker monitoring | Custom `/workers` endpoint | Flower (`mher/flower`) | Real-time task stream, worker status, task history, rate limiting, REST API |
| Task routing | Manual queue selection logic | Celery `task_routes` config | Built-in routing by task name or queue label |

**Key insight:** The retry + backoff problem has subtle correctness requirements (jitter to prevent thundering herd, acks_late to prevent message loss). Hand-rolling this adds at least 50 lines of error-prone code. Celery provides it in three decorator kwargs.

---

## Common Pitfalls

### Pitfall 1: Circular Import Between worker.py and FastAPI App
**What goes wrong:** `worker.py` imports from `container.py` to get the Redis URL → `container.py` imports from services → services import from FastAPI → Celery worker fails to start with `ImportError`.
**Why it happens:** The worker process runs `celery -A src.infrastructure.tasks.worker worker`. If `worker.py` transitively imports the FastAPI app, the entire application boots in the worker process.
**How to avoid:** `worker.py` reads `REDIS_URL` directly from `os.environ`. It never imports from `container.py`, `main.py`, or any router.
**Warning signs:** Worker startup prints FastAPI startup logs or raises `RuntimeError: This event loop is already running`.

### Pitfall 2: async def Task Body Never Awaited
**What goes wrong:** Task defined as `async def notify_new_record(...)`. Worker calls it, sees a coroutine object, returns it immediately without executing the body. Looks like it worked (no exception) but nothing happened.
**Why it happens:** Celery's prefork pool calls tasks synchronously. Async def returns a coroutine object in sync context.
**How to avoid:** Keep task bodies as `def` (sync). If you need async, use `asyncio.run()` wrapper pattern.
**Warning signs:** Task shows SUCCESS in Flower but side effects never occurred.

### Pitfall 3: Redis Key Collision Between Celery and RedisEventBus
**What goes wrong:** Celery stores broker messages and results in Redis DB 0. The existing `RedisEventBus` also connects to the same URL (DB 0). Under load, Celery's BLPOP calls and the event bus's pub/sub can interfere.
**Why it happens:** Both use the same Redis database index.
**How to avoid (this slice):** Not a problem for a stub task at low volume. For the learning doc, note that production should use separate DB indices: `redis://redis:6379/0` for Celery, `redis://redis:6379/1` for the event bus.
**Warning signs:** Tasks disappear from queue randomly; pub/sub messages trigger task workers.

### Pitfall 4: task_always_eager=True Left On in Tests
**What goes wrong:** Setting `task_always_eager=True` (deprecated but common in tutorials) causes tasks to run synchronously and inline in tests. Tests pass but worker behavior is never actually tested.
**Why it happens:** It's a popular tutorial shortcut to avoid needing Redis in tests.
**How to avoid:** For unit tests, patch `.delay` with `MagicMock()`. For integration tests, use `task_always_eager` only in the test fixture scope, not globally.
**Warning signs:** All task tests pass even when Redis is not running.

### Pitfall 5: .delay() Returns Before Commit in Same Transaction
**What goes wrong:** Task fires before `session.commit()` completes. Worker queries DB for the record — it doesn't exist yet. Task fails or processes stale data.
**Why it happens:** `.delay()` publishes to Redis immediately. If called before `await session.commit()`, the worker can receive and process the task before the DB write commits.
**How to avoid:** Always call `.delay()` AFTER `await session.commit()`. This is a strict ordering requirement.
**Warning signs:** Task logs `record not found` errors; intermittent failures under load.

---

## Code Examples

### Complete docker-compose additions for Celery + Flower
```yaml
# Add to existing docker-compose.yml services:

  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A src.infrastructure.tasks.worker.celery_app worker --loglevel=info --concurrency=2
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql+asyncpg://emotionai:password123@db:5432/emotionai_db
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=development
    depends_on:
      redis:
        condition: service_healthy
      db:
        condition: service_healthy
    networks:
      - emotionai-network

  flower:
    image: mher/flower:2.0
    command: celery --broker=redis://redis:6379/0 flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery_worker
    networks:
      - emotionai-network
```

Key details:
- Worker command: `-A src.infrastructure.tasks.worker.celery_app` — the dotted path to the Celery app instance (not the module, the instance).
- `--concurrency=2` — 2 prefork processes. Fine for dev. Default is number of CPUs.
- Flower uses `mher/flower:2.0` image (official). No OPENAI_API_KEY needed in worker for the stub.

### Worker Start Command (standalone, for verification)
```bash
# From the project root (inside container or with venv active):
celery -A src.infrastructure.tasks.worker.celery_app worker --loglevel=info

# Check Flower at:
# http://localhost:5555
```

### Test: Verify Task is Triggered (pytest pattern)
```python
# tests/infrastructure/tasks/test_notification_tasks.py
from unittest.mock import patch, MagicMock
from src.infrastructure.tasks.notification_tasks import notify_new_record


def test_notify_new_record_task_body():
    """Task executes synchronously and returns expected dict."""
    result = notify_new_record.run("test-record-id", "test-user-id")
    assert result["status"] == "notified"
    assert result["record_id"] == "test-record-id"


def test_notify_task_is_dispatched_from_router(client, mock_container):
    """POST /emotional_records fires the Celery task after commit."""
    with patch(
        "src.presentation.api.routers.records.notify_new_record.delay"
    ) as mock_delay:
        response = client.post("/v1/api/emotional_records/", json={...})
        assert response.status_code == 200
        mock_delay.assert_called_once()
        args = mock_delay.call_args[0]
        assert args[1] == str(user_id)  # user_id is second arg
```

`.run()` invokes the task body directly without going through the broker — correct for unit testing task logic. `.delay` is patched as a MagicMock for router tests.

---

## Hook Points in EmotionAI: Priority List

Based on reading the codebase, these are the endpoints where async task offloading adds the most value (ordered by priority):

| Priority | Endpoint | Current Behavior | Async Opportunity |
|----------|----------|-----------------|-------------------|
| 1 (this slice) | `POST /v1/api/emotional_records/` | Saves record, broadcasts WS event | Add: `notify_new_record.delay(record_id, user_id)` after commit |
| 2 (this slice, second hook) | `POST /v1/api/emotional_records/from_custom_emotion` | Same flow with custom emotion | Same task dispatch pattern |
| 3 (future — Milestone 3) | `POST /v1/api/chat` | Calls OpenAI tagging synchronously in `AgentChatUseCase` | Move `OpenAITaggingService.extract_tags_from_message()` to Celery task |
| 4 (future — Milestone 3) | After any record save | `processed_for_tags=False` records never get tags | Background tag processing job triggered here |

The `OpenAITaggingService` is explicitly identified in TECH_DEBT.md as making blocking sync calls in async handlers. This is the ideal future candidate, but is deferred per CONTEXT.md.

---

## Task Queue Mental Model (for learning doc)

This section is reference material for `docs/learning/celery_redis.md`:

```
REQUEST LIFECYCLE WITH CELERY:

1. FastAPI endpoint receives HTTP request
2. Request handler writes to PostgreSQL (await session.commit())
3. Handler calls: notify_new_record.delay(record_id, user_id)
   → Serializes args to JSON
   → Publishes message to Redis list key "celery" (the default queue)
   → Returns task_id immediately (non-blocking)
4. HTTP response returned to client (fast — no waiting for task)

WORKER LIFECYCLE:
1. celery worker process starts, connects to Redis
2. Worker BLPOPs (blocking pop) on the "celery" queue key
3. Message arrives → worker deserializes → calls notify_new_record(record_id, user_id)
4. Task executes synchronously in worker process
5. Worker writes result to Redis result backend key: celery-task-meta-{task_id}
6. Result expires after result_expires seconds (86400 = 24h)

KEY VOCABULARY:
- Broker: Redis — stores the queue of pending tasks
- Backend: Redis — stores completed task results
- Worker: Separate OS process running tasks from the queue
- Task: Python function decorated with @shared_task
- task_id: UUID assigned when .delay() is called — used to poll status
- PENDING → STARTED → SUCCESS/FAILURE/RETRY — task state machine
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `task_always_eager` for tests | Patch `.delay` with MagicMock | Celery 4+ deprecated eager | Tests now actually verify dispatch, not inline execution |
| `celery.conf.BROKER_URL` (uppercase) | `celery.conf.broker_url` (lowercase) | Celery 4.0 | Lowercase config is current; uppercase still works but is deprecated |
| `@app.task` on all tasks | `@shared_task` for library/module tasks | Celery 3+ | Avoids importing app instance in task modules — cleaner architecture |
| `result_backend='redis://...'` keyword | Set via `celery_app.conf.update()` | Celery 4+ | `conf.update()` is the idiomatic bulk-config pattern |
| `async def` tasks with gevent pool | `def` tasks + `asyncio.run()` for async body | Still current | gevent adds complexity; asyncio.run() is simpler for occasional async |

**Deprecated/outdated:**
- `CELERY_BROKER_URL` (uppercase env var): still read by some versions but use `CELERY_BROKER_URL` only as env var name, set `conf.broker_url` in code
- `task_always_eager`: deprecated in Celery 5.x; use `task_always_eager` only in test fixtures with explicit scope

---

## Open Questions

1. **Redis DB collision with RedisEventBus**
   - What we know: Both Celery and `RedisEventBus` use `REDIS_URL` which defaults to DB 0
   - What's unclear: Whether pub/sub and BLPOP on the same DB index causes real interference at the stub task volume
   - Recommendation: Use the same URL for now (low volume stub); add a note in the learning doc about separate DB indices for production. No code change needed this slice.

2. **Celery worker needs OPENAI_API_KEY in docker-compose env**
   - What we know: The stub task does not call OpenAI. Future tasks (tagging) will.
   - What's unclear: Whether to add OPENAI_API_KEY to the worker service now (future-proof) or leave it out (YAGNI for this slice)
   - Recommendation: Omit from worker service for this slice (stub doesn't need it). Add when tagging is moved to Celery in Milestone 3.

3. **Celery worker and `src.` package resolution**
   - What we know: The worker command is `celery -A src.infrastructure.tasks.worker.celery_app worker`. This requires that the project root (where `src/` lives) is in PYTHONPATH.
   - What's unclear: Whether the existing Dockerfile sets PYTHONPATH correctly.
   - Recommendation: Check Dockerfile WORKDIR and PYTHONPATH. Add `PYTHONPATH=/app` to the worker service env vars in docker-compose as a safety net.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x with asyncio_mode=auto |
| Config file | `pyproject.toml` (exists — `[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/infrastructure/tasks/ -x -q` |
| Full suite command | `pytest --cov=src --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| m2s2-01 | `notify_new_record` task body executes and returns correct dict | unit | `pytest tests/infrastructure/tasks/test_notification_tasks.py -x` | No — Wave 0 |
| m2s2-02 | Task dispatch fires after `POST /v1/api/emotional_records/` commit | integration (mock `.delay`) | `pytest tests/infrastructure/tasks/test_task_dispatch.py -x` | No — Wave 0 |
| m2s2-03 | Celery worker starts without import errors | smoke (manual / CI) | `celery -A src.infrastructure.tasks.worker.celery_app inspect ping` | No — Wave 0 |
| m2s2-04 | Flower UI shows task in completed list | manual verification | Navigate to `http://localhost:5555` | N/A — manual |

### Sampling Rate
- **Per task commit:** `pytest tests/infrastructure/tasks/ -x -q`
- **Per wave merge:** `pytest --cov=src --cov-report=term-missing`
- **Phase gate:** Full suite green (all Milestone 1 tests still passing) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/infrastructure/__init__.py` — package init for new test subtree
- [ ] `tests/infrastructure/tasks/__init__.py` — package init
- [ ] `tests/infrastructure/tasks/test_notification_tasks.py` — covers m2s2-01
- [ ] `tests/infrastructure/tasks/test_task_dispatch.py` — covers m2s2-02 (requires TestClient fixture)
- [ ] `src/infrastructure/tasks/__init__.py` — makes tasks a Python package
- [ ] `src/infrastructure/tasks/worker.py` — Celery app instance
- [ ] `src/infrastructure/tasks/notification_tasks.py` — stub task definition

---

## Sources

### Primary (HIGH confidence)
- [Celery 5.x Official Tasks Docs](https://docs.celeryq.dev/en/stable/userguide/tasks.html) — shared_task, autoretry_for, retry_backoff, acks_late, result_expires
- [TestDriven.io: Async Tasks with FastAPI and Celery](https://testdriven.io/blog/fastapi-and-celery/) — .delay() pattern, docker-compose layout, AsyncResult usage
- [Celery + Flower Docker Compose](https://docker.recipes/messaging/celery-flower) — confirmed mher/flower:2.0 image, port 5555

### Secondary (MEDIUM confidence)
- [FastAPI BackgroundTasks vs ARQ vs Celery comparison](https://medium.com/@komalbaparmar007/fastapi-background-tasks-vs-celery-vs-arq-picking-the-right-asynchronous-workhorse-b6e0478ecf4a) — feature comparison table, use case guidance
- [Building FastAPI + Celery + Flower + Docker (2024)](https://nuttaphat.com/posts/2024/10/building-high-performance-application-with-fastapi-redis-celery-flower-docker/) — docker-compose service definitions verified against official docs
- [Celery @shared_task options guide (2024)](https://blog.mikihands.com/en/whitedec/2024/12/15/celery-shared-task-options/) — bind, autoretry_for, retry_backoff patterns
- [Celery Github Discussion: async in tasks](https://github.com/celery/celery/discussions/9058) — asyncio.run() pattern confirmed as community standard

### Tertiary (LOW confidence)
- Various Medium articles on Celery/FastAPI integration — patterns cross-verified against official docs before inclusion

---

## Metadata

**Confidence breakdown:**
- Standard stack (Celery 5.x, redis, flower): HIGH — official docs + TestDriven.io verified
- Architecture (worker.py isolation, shared_task, .delay() placement): HIGH — official docs + codebase analysis
- Async/sync tension and asyncio.run() pattern: HIGH — official Python docs + GitHub discussions
- docker-compose additions: MEDIUM — pattern verified against official examples, exact image tags need verification at build time
- Pitfalls: HIGH — derived from codebase analysis (circular import risk is real given container.py structure) + community sources

**Research date:** 2026-03-19
**Valid until:** 2026-07-01 (Celery 5.x is stable; check for 5.4+ release notes if using after this date)
