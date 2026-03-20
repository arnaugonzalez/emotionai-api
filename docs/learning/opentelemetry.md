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
