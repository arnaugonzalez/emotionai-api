# OpenTelemetry — EmotionAI Study Guide

> Personal reference written while implementing OTEL tracing in the EmotionAI API.
> All examples use real span names and real file paths from this project.

---

## What is it and why do we use it here

Observability has three pillars — you need all three to debug production systems:

| Pillar | Tool | Question answered |
|--------|------|-------------------|
| Metrics | Prometheus | "How many?" "How fast?" "Is the error rate spiking?" |
| Logs | Structured log lines | "What happened?" "What was the value at that moment?" |
| Traces | OpenTelemetry | "Why is this request slow?" "Which function took 3 seconds?" |

In EmotionAI, every chat request calls GPT-4 (via LangChain) and then GPT-4o-mini (for semantic
tagging). Without tracing, you see one slow HTTP span in Jaeger but have no visibility into
which step inside the handler was slow. With manual spans you get the full call chain:

```
POST /v1/api/chat (FastAPI auto-instrumented)
  └── emotionai.chat.llm_generate (LangChainAgentService.send_message)
        └── POST https://api.openai.com/v1/chat/completions (httpx auto-instrumented)
  └── emotionai.tagging.classify (OpenAITaggingService.extract_tags_from_message)
        └── POST https://api.openai.com/v1/chat/completions (httpx auto-instrumented)
```

This trace shows you instantly: was it the LangChain call or the tagging call that was slow?

---

## Core concepts

### Trace vs Span

A **trace** is the entire journey of one request. It has a globally unique `trace_id` (16 bytes).

A **span** is one unit of work within that trace. It has:
- A `name` (e.g. `emotionai.chat.llm_generate`)
- A `trace_id` linking it to its parent trace
- A `span_id` (its own unique ID)
- `start_time` and `end_time` — this is how Jaeger shows you durations
- `attributes` — key-value pairs (e.g. `user.id`, `llm.model`)
- `status` — UNSET, OK, or ERROR

### Parent-child relationships

Spans form a tree. The first span in a request is the root. Each child span knows its parent's
`span_id`. This is how Jaeger renders the waterfall view.

In EmotionAI the hierarchy is:

```
FastAPI root span (auto-created by FastAPIInstrumentor)
  └── emotionai.chat.llm_generate (manual, LangChainAgentService)
        └── HTTP POST openai.com (auto-created by HTTPXClientInstrumentor)
  └── emotionai.tagging.classify (manual, OpenAITaggingService)
        └── HTTP POST openai.com (auto-created by HTTPXClientInstrumentor)
  └── asyncpg query spans (auto-created by AsyncPGInstrumentor)
```

### Context propagation

When `send_message` creates a child span, how does OTEL know which trace to attach it to?
Answer: the `Context` object. OTEL stores the active span in a Python `ContextVar`. Every time
you call `start_as_current_span`, it reads the current context, creates a child, and sets that
child as the new current span for the duration of the `with` block.

For asyncio, context propagation is automatic — each task inherits a copy of the context
from its creator. You don't need to pass trace IDs manually.

---

## How it is wired in EmotionAI

### Initialization: `src/infrastructure/telemetry/tracing.py`

```python
def setup_tracing(service_name, service_version, environment, otlp_endpoint, enabled=True):
    resource = Resource.create({SERVICE_NAME: service_name, ...})
    exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    AsyncPGInstrumentor().instrument()
    HTTPXClientInstrumentor().instrument()
```

**Why in lifespan, not at module level?**
`uvicorn --reload` forks new worker processes. If OTEL is initialized at module import time,
each reload creates a new `TracerProvider` but the old one's `BatchSpanProcessor` thread is
still running in the parent process. This causes duplicate spans and leaked threads.
Initializing inside FastAPI's `lifespan` context manager means it runs once per process
startup, cleanly.

`setup_tracing()` is called before `initialize_container()` so that `AsyncPGInstrumentor`
patches the asyncpg driver before any database connections are created.

### Getting a tracer: `get_tracer(__name__)`

```python
# src/infrastructure/services/langchain_agent_service.py
from ...infrastructure.telemetry.tracing import get_tracer

class LangChainAgentService(IAgentService):
    _tracer = get_tracer(__name__)
```

`get_tracer(__name__)` returns a `Tracer` from the globally registered `TracerProvider`.
If `setup_tracing()` has not been called (e.g. during unit tests with no Jaeger), this
returns a no-op `Tracer` — spans are created as no-op objects and no errors are raised.

The module name (`__name__`) becomes the **instrumentation scope** in Jaeger, displayed as
the library/component that created the span.

---

## The critical async pattern

### WRONG — decorator form, silent 0-second spans

```python
@tracer.start_as_current_span("emotionai.chat.llm_generate")
async def send_message(self, ...):
    result = await self.llm_service.generate_therapy_response(...)
    return result
```

The decorator wraps the coroutine factory, not the coroutine execution. The span is started
and immediately ended when the coroutine object is created — before any `await` runs.
Result: span duration is always 0 microseconds.

### CORRECT — context manager form

```python
async def send_message(self, user_id, agent_type, message, context):
    with self._tracer.start_as_current_span("emotionai.chat.llm_generate") as span:
        span.set_attribute("user.id", str(user_id))
        span.set_attribute("llm.model", "gpt-4")
        span.set_attribute("chat.agent_type", agent_type)

        result = await self.llm_service.generate_therapy_response(agent_context, message)

        span.set_attribute("chat.therapeutic_approach", result.therapeutic_approach)
        return result
```

The `with` block correctly spans the duration from before the `await` to after it returns.
The span is ended when the `with` block exits, whether that is via return or exception.

---

## InMemorySpanExporter in tests

Unit tests should not require Jaeger to be running. `InMemorySpanExporter` captures spans
in memory for assertions. Because the OTEL SDK prevents overriding the global
`TracerProvider` after it has been set once (a safety measure to avoid races), tests inject
the tracer directly onto the service instance:

```python
# tests/unit/test_langchain_spans.py
@pytest.fixture
def span_exporter():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield exporter, provider
    exporter.clear()

async def test_llm_generate_creates_span(span_exporter):
    exporter, provider = span_exporter
    service = _make_service(provider)
    # Inject test-local tracer — bypasses global provider restriction
    service._tracer = provider.get_tracer(__name__)

    await service.send_message(uuid4(), "therapy", "I feel anxious", {})

    spans = exporter.get_finished_spans()
    assert any(s.name == "emotionai.chat.llm_generate" for s in spans)
```

`SimpleSpanProcessor` (vs `BatchSpanProcessor`) exports spans synchronously, so
`get_finished_spans()` is immediately consistent after the `await` returns.

---

## Span attributes in this project

| Attribute | Set on | Example value | Why useful |
|-----------|--------|---------------|------------|
| `user.id` | `emotionai.chat.llm_generate` | `"a1b2c3d4-..."` | Filter traces for one user in Jaeger |
| `llm.model` | both spans | `"gpt-4"`, `"gpt-4o-mini"` | Compare latency by model |
| `chat.agent_type` | `emotionai.chat.llm_generate` | `"therapy"`, `"wellness"` | Split traces by agent |
| `input.length` | `emotionai.tagging.classify` | `47` | Detect unusually large prompts |
| `tagging.content_type` | `emotionai.tagging.classify` | `"message"` | Filter by what was tagged |
| `tagging.tag_count` | `emotionai.tagging.classify` | `5` | Monitor tagging quality |
| `crisis_detected` | `emotionai.chat.llm_generate` | `True` | Alert on crisis sessions |

---

## Common mistakes and how to avoid them

**1. Decorator form on async → silent 0-second spans**
Use `with tracer.start_as_current_span(...)` inside the async function body.

**2. Missing `/v1/traces` suffix in OTLP endpoint → silent span loss**
`OTLPSpanExporter` appends `/v1/traces` internally. Pass the base URL only:
`OTLPSpanExporter(endpoint="http://jaeger:4318/v1/traces")` ← this would double the path.
Correct: `OTLPSpanExporter(endpoint="http://jaeger:4318")` — see `tracing.py` line 45.

**3. Module-level init → broken uvicorn reload**
Initialize inside FastAPI lifespan, not at the top of a module.

**4. `SQLAlchemyInstrumentor` → doesn't work with asyncpg**
Use `AsyncPGInstrumentor` from `opentelemetry-instrumentation-asyncpg` instead.
SQLAlchemy's async layer translates calls into asyncpg — only asyncpg sees the actual
network calls.

**5. Not clearing InMemorySpanExporter between tests → span bleed**
Always call `exporter.clear()` in fixture teardown, or spans from test N appear in test N+1.

---

## Further reading

- [OpenTelemetry Python SDK](https://opentelemetry-python.readthedocs.io/)
- [Jaeger documentation](https://www.jaegertracing.io/docs/)
- [OTLP specification](https://opentelemetry.io/docs/specs/otlp/)
- [Semantic conventions for HTTP spans](https://opentelemetry.io/docs/specs/semconv/http/)

## When to use OpenTelemetry (vs alternatives)

| Scenario | Best tool | Why |
|----------|-----------|-----|
| "Why was *this specific request* slow?" | OTel traces | Per-request waterfall shows which span took the time. |
| "Is the error *rate* trending up?" | Prometheus metrics | Aggregate counters and `rate()` expressions. |
| "What was the payload that caused this error?" | Structured logs | Logs carry arbitrary key-value context; spans carry structured attributes. |
| Distributed system — trace across 3 services | OTel + W3C Trace Context propagation | `traceparent` header carries trace_id across HTTP boundaries automatically. |
| Single process — all work in one Python function | Logs or Prometheus | OTel overhead is not worth it for a single in-process function with no I/O. |
| Debug a slow DB query | AsyncPGInstrumentor (OTel) | Auto-instrumentation creates a child span per query — no manual code required. |
| Debug a slow OpenAI call | HTTPXClientInstrumentor (OTel) | Auto-instruments all httpx requests with URL, method, status, duration. |
| Alert when p95 LLM latency exceeds 5s | Prometheus Histogram | `histogram_quantile(0.95, ...)` + Alertmanager rule. OTel alone cannot alert. |

EmotionAI uses all three pillars. Traces answer the "which span?" question that metrics and logs
alone cannot answer for a multi-step handler calling LLM + tagging + database.

## Advanced code examples

### Recording error status on a span

```python
from opentelemetry.trace import StatusCode

async def send_message(self, user_id, agent_type, message, context):
    with self._tracer.start_as_current_span("emotionai.chat.llm_generate") as span:
        span.set_attribute("user.id", str(user_id))
        try:
            result = await self.llm_service.generate_therapy_response(...)
            span.set_status(StatusCode.OK)
            return result
        except Exception as exc:
            span.set_status(StatusCode.ERROR, description=str(exc))
            span.record_exception(exc)
            raise
```

`record_exception()` attaches the exception type, message, and stack trace as span events.
Jaeger renders these as structured event rows under the span. Without this, an error span
shows as ERROR status with no details.

### Adding a span event (lightweight breadcrumb)

```python
with self._tracer.start_as_current_span("emotionai.chat.llm_generate") as span:
    span.add_event("context_built", {"context_length": len(context)})
    result = await self.llm_service.generate_therapy_response(...)
    span.add_event("llm_response_received", {"token_count": result.token_count})
```

Events are timestamped points within the span. Use them for intermediate milestones when you
do not want the overhead of a full child span.

### Propagating trace context to a Celery task

OTel context does not cross process boundaries automatically for Celery. Inject the current
context into the task arguments:

```python
from opentelemetry.propagate import inject

def _enqueue_record_notification(record_id: str, user_id: str) -> None:
    carrier = {}
    inject(carrier)  # writes traceparent/tracestate into carrier dict
    try:
        notify_new_record.delay(record_id, user_id, otel_carrier=carrier)
    except Exception:
        logger.exception("Failed to enqueue notify_new_record task")
```

Inside the Celery task, extract and attach:

```python
from opentelemetry.propagate import extract
from opentelemetry import trace, context as otel_context

def notify_new_record(self, record_id, user_id, otel_carrier=None):
    ctx = extract(otel_carrier or {})
    token = otel_context.attach(ctx)
    try:
        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span("emotionai.notify_new_record"):
            ...
    finally:
        otel_context.detach(token)
```

This is not implemented in EmotionAI today but is the canonical pattern for cross-process trace
continuity.

### Checking spans in integration tests

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

def make_test_provider():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter

async def test_chat_creates_llm_span():
    provider, exporter = make_test_provider()
    service = LangChainAgentService(...)
    service._tracer = provider.get_tracer(__name__)  # inject test tracer

    await service.send_message(uuid4(), "therapy", "I feel anxious", {})

    spans = exporter.get_finished_spans()
    llm_span = next(s for s in spans if s.name == "emotionai.chat.llm_generate")
    assert llm_span.attributes["user.id"] is not None
    assert llm_span.status.status_code == StatusCode.OK
```

`SimpleSpanProcessor` exports synchronously — no need to flush or wait after `await`.
`BatchSpanProcessor` is async and requires explicit `provider.force_flush()` before asserting.

## Interview Prep — OpenTelemetry

**Q1: What are the three pillars of observability? What question does each answer?**

Metrics (Prometheus): "How many, how fast, is the error rate spiking?" Aggregate signals across
all requests. Logs: "What happened in this specific execution? What was the value at that moment?"
Traces (OpenTelemetry): "Why was this request slow? Which function inside the handler took 3
seconds?" EmotionAI uses all three: Prometheus for aggregate signals, structured logs for event
detail, OTel spans for the per-request call chain (FastAPI → LangChain → OpenAI → asyncpg).

**Q2: What is the difference between a Trace and a Span?**

A trace is the complete journey of one request from entry to exit, identified by a 16-byte
`trace_id`. A span is one unit of work within that trace: one function call, one DB query, one
HTTP request to OpenAI. Spans have their own `span_id`, a reference to their parent `span_id`,
`start_time`, `end_time`, key-value `attributes`, and a `status`. The tree of spans within one
`trace_id` is what Jaeger renders as the waterfall view.

**Q3: Why does the decorator form of `start_as_current_span` produce silent 0-second spans on async functions?**

The `@tracer.start_as_current_span(...)` decorator wraps the coroutine *factory* function. When
called, it starts the span, immediately calls the factory (which returns a coroutine object, not
the executed coroutine), and immediately ends the span. The actual async execution happens later
when the coroutine is awaited — outside the span. Result: the span records 0 microseconds. The
fix is always `with tracer.start_as_current_span(...):` inside the async function body.

**Q4: How does OpenTelemetry propagate context across async tasks in Python?**

OTEL stores the active span in a Python `ContextVar`. `asyncio` copies the `contextvars` context
when spawning a new task (via `asyncio.create_task`), so child tasks inherit the parent's active
span automatically. This means database queries inside `asyncpg` coroutines spawned during
request handling automatically become children of the HTTP root span — no manual context passing
required within a single process.

**Q5: Why is `setup_tracing()` called before `initialize_container()` in EmotionAI's lifespan?**

`AsyncPGInstrumentor` works by monkey-patching the asyncpg driver. It must patch the driver
before any connection pools are created. If `initialize_container()` ran first, the SQLAlchemy
async engine and connection pool would already be initialized with un-patched asyncpg. Subsequent
database spans would not appear in Jaeger.

**Q6: Why does OTEL use `BatchSpanProcessor` in production but tests use `SimpleSpanProcessor`?**

`BatchSpanProcessor` collects spans in memory and exports them in background batches to reduce
export overhead — suitable for production where you want minimal latency impact. But in tests,
batch export is asynchronous: `get_finished_spans()` after an `await` may return empty because
the batch has not flushed yet. `SimpleSpanProcessor` exports synchronously on every span end,
so `get_finished_spans()` is immediately consistent in tests.

**Q7: What does `get_tracer(__name__)` do and what is the instrumentation scope?**

`get_tracer(__name__)` returns a `Tracer` from the globally registered `TracerProvider`.
The `__name__` argument sets the instrumentation scope — the library or component name that
Jaeger displays as the span source. In `langchain_agent_service.py`, `__name__` is
`src.infrastructure.services.langchain_agent_service`. If `setup_tracing()` has not been called
(e.g. unit tests with no Jaeger), this returns a no-op `Tracer` that creates spans as no-op
objects — no exceptions, no side effects.

**Q8: What is W3C Trace Context and why does it matter for distributed systems?**

W3C Trace Context is a standard HTTP header pair (`traceparent`, `tracestate`) that carries
a trace ID and parent span ID across process boundaries. When Service A calls Service B over
HTTP, Service A injects these headers. Service B's OTEL instrumentation extracts them and
creates its root span as a child of Service A's span. Result: the trace flows seamlessly across
both services in Jaeger. Without this, each service shows isolated traces with no connection.
HTTPXClientInstrumentor in EmotionAI automatically injects `traceparent` into outgoing OpenAI
calls.

**Q9: What is the OTLP endpoint configuration gotcha in EmotionAI?**

`OTLPSpanExporter` appends `/v1/traces` internally when you use the gRPC transport. The HTTP
transport (`OTLPSpanExporter(endpoint="...")`) also appends `/v1/traces`. So you pass the base
URL only: `OTLPSpanExporter(endpoint="http://jaeger:4318")`. Passing
`endpoint="http://jaeger:4318/v1/traces"` doubles the path to `.../v1/traces/v1/traces` and
spans are silently lost with no error — the exporter returns OK but Jaeger receives nothing
it can parse at that path.

**Q10: How would you add a span for the `extract_tags_from_message` tagging call and make it show as a child of the LLM span?**

OTEL's context propagation handles parent-child automatically via `ContextVar`. As long as
`extract_tags_from_message` is called *inside* the `with self._tracer.start_as_current_span("emotionai.chat.llm_generate"):` block, any new span created inside it will automatically be
a child. In `openai_tagging_service.py`:

```python
with self._tracer.start_as_current_span("emotionai.tagging.classify") as span:
    span.set_attribute("input.length", len(message))
    result = await self._openai_client.chat(...)
```

If this runs while the LLM span is active, Jaeger shows `emotionai.tagging.classify` nested
under `emotionai.chat.llm_generate` automatically.

## Gotchas interviewers test on

**"What is the decorator form bug and how do you detect it in Jaeger?"**
Using `@tracer.start_as_current_span(...)` on an `async def` function produces spans with
duration 0 microseconds. In Jaeger they appear as a thin vertical line on the waterfall with
`0ms` displayed. The span is still named and shows in the trace — it just looks meaninglessly
fast. The fix is the context manager form inside the function body.

**"Why can't you call `trace.set_tracer_provider()` twice?"**
The OTEL SDK is designed to set the global provider once. A second call raises a warning and
the second provider is ignored. This is why tests cannot simply call `setup_tracing()` — the
first test call sets the global, and subsequent tests inherit it. EmotionAI's test pattern
injects the test tracer directly onto `service._tracer` instead of touching the global provider.

**"What happens to spans if Jaeger is unreachable?"**
`BatchSpanProcessor` with `OTLPSpanExporter` drops spans silently after retries. The application
continues running normally. No exception propagates to request handlers. This is intentional —
telemetry infrastructure failure should never cause service outages. The tradeoff: you lose
observability during a Jaeger outage, but your API stays up.

**"What is `InMemorySpanExporter.clear()` and why is it needed in test fixtures?"**
`InMemorySpanExporter` accumulates spans across all calls to `get_finished_spans()`. Without
calling `clear()` in fixture teardown, spans from test N are still present when test N+1 runs.
Assertions in test N+1 may incorrectly pass because they find spans from test N. EmotionAI's
test fixture calls `exporter.clear()` in the `finally` block of the `yield` fixture.

**"Does `AsyncPGInstrumentor` instrument SQLAlchemy queries?"**
It instruments asyncpg — the underlying driver that SQLAlchemy's async engine delegates to.
SQLAlchemy query construction happens in Python and is not instrumented, but the actual network
call to PostgreSQL (which goes through asyncpg) creates a span. This means you see the raw SQL
queries in Jaeger spans but not the ORM-level method calls. `SQLAlchemyInstrumentor` instruments
the ORM layer but does not work with asyncpg — that is why EmotionAI uses `AsyncPGInstrumentor`.
