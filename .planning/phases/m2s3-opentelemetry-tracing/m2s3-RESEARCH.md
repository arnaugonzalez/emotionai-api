# Phase m2s3: OpenTelemetry Tracing — Research

**Researched:** 2026-03-19
**Domain:** OpenTelemetry distributed tracing — Python SDK, FastAPI auto-instrumentation, LangChain manual spans, Jaeger
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use Jaeger all-in-one Docker image (simplest — no OpenTelemetry Collector needed for local dev)
- OTLP exporter over HTTP (port 4318) — easier than gRPC for local dev
- Auto-instrument FastAPI, SQLAlchemy, and httpx if available instrumentors exist
- Focus manual spans on the slowest call chains: LangChain agent (multiple LLM calls), OpenAI tagging pipeline
- Span naming convention: `emotionai.chat.generate`, `emotionai.tagging.classify`, `emotionai.db.query`

### Claude's Discretion
- Whether to use `opentelemetry-sdk` directly or `opentelemetry-distro` (distro package auto-detects instrumentors)
- Sampling strategy (always-on for dev, parentbased for prod — document both)
- Resource attributes to set (service.name, service.version, deployment.environment)
- Whether to instrument Redis calls (nice-to-have, not required)

### Deferred Ideas (OUT OF SCOPE)
- OpenTelemetry Collector (add when moving to production export)
- Metrics via OTEL (overlap with Prometheus slice — keep separate)
- Log correlation (trace ID injection into structlog/logging)
- Baggage propagation across service boundaries
</user_constraints>

---

## Summary

OpenTelemetry Python has a well-maintained ecosystem for FastAPI. The `opentelemetry-instrumentation-fastapi` package (part of opentelemetry-python-contrib, maintained by the CNCF OpenTelemetry project) provides zero-code auto-instrumentation via a single `FastAPIInstrumentor.instrument_app(app)` call. Async context propagation works correctly in Python 3.11 using `contextvars` — there are no special workarounds needed as long as spans are created with the `with tracer.start_as_current_span(...)` context manager (not the decorator form, which has a known resolved bug).

For LangChain, `opentelemetry-instrumentation-langchain` (PyPI package from Traceloop/OpenLLMetry, version 0.52.5 as of Feb 2026) provides automatic LangChain instrumentation that exports standard OTLP spans. It is NOT locked to LangSmith or any proprietary backend — it works with any OTLP-compatible backend including Jaeger. However, since EmotionAI's `LangChainAgentService` does not use the high-level LangChain LCEL/chain abstractions (it calls `llm_service.generate_therapy_response()` via a custom service interface), the auto-instrumentor will not capture those calls. Manual spans are needed and are the correct approach here.

Jaeger all-in-one (v1.76) natively accepts OTLP HTTP on port 4318 — no `COLLECTOR_OTLP_ENABLED=true` environment variable is required in recent versions. The UI runs at port 16686.

**Primary recommendation:** Use `opentelemetry-sdk` directly (not distro) for explicit control. Initialize the TracerProvider in `main.py`'s `lifespan` context manager. Use `FastAPIInstrumentor.instrument_app()` for zero-code HTTP span capture. Add manual spans around the 6 key LangChain service methods. Use `opentelemetry-instrumentation-asyncpg` (not the SQLAlchemy wrapper) for database spans since EmotionAI uses async engines.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `opentelemetry-api` | >=1.25.0 | Tracing API (tracer, span interfaces) | Vendor-neutral API layer — stable, never changes |
| `opentelemetry-sdk` | >=1.25.0 | SDK with TracerProvider, processors, exporters | The reference implementation — required with any OTLP exporter |
| `opentelemetry-exporter-otlp-proto-http` | >=1.25.0 | OTLP HTTP exporter to Jaeger port 4318 | HTTP (not gRPC) is simpler for local dev — no protobuf compilation |
| `opentelemetry-instrumentation-fastapi` | >=0.46b0 | Auto-instrument all FastAPI routes | Zero-code; captures method, URL, status, latency |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `opentelemetry-instrumentation-asyncpg` | >=0.46b0 | Instrument asyncpg database calls | Use instead of SQLAlchemy instrumentor for async engines — captures actual SQL |
| `opentelemetry-instrumentation-httpx` | >=0.46b0 | Instrument outbound HTTP (OpenAI API calls via httpx) | Captures outbound HTTP to OpenAI as child spans |
| `opentelemetry-instrumentation-langchain` | >=0.30.0 | Auto-instrument LangChain LCEL chains | Only useful if using LangChain chains/agents directly — NOT useful here since LangChainAgentService wraps a custom ILLMService interface |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `opentelemetry-exporter-otlp-proto-http` | `opentelemetry-exporter-otlp-proto-grpc` | gRPC requires port 4317 and protobuf runtime; no advantage for local dev |
| `opentelemetry-sdk` directly | `opentelemetry-distro` | distro adds `opentelemetry-instrument` CLI tool but forces process-level injection; harder to control initialization order in lifespan |
| Manual spans in LangChainAgentService | `opentelemetry-instrumentation-langchain` | Langchain instrumentor traces LCEL chain objects, not custom service wrappers; manual spans give named spans matching EmotionAI conventions |

**Installation:**
```bash
pip install \
  opentelemetry-api \
  opentelemetry-sdk \
  "opentelemetry-exporter-otlp-proto-http>=1.25.0" \
  opentelemetry-instrumentation-fastapi \
  opentelemetry-instrumentation-asyncpg \
  opentelemetry-instrumentation-httpx
```

> Note: opentelemetry-api and opentelemetry-sdk versions must match exactly. Pin to the same minor version.

---

## Architecture Patterns

### Recommended Project Structure
```
src/
├── infrastructure/
│   ├── config/
│   │   └── settings.py          # Add: otel_endpoint, otel_service_name, otel_enabled
│   └── telemetry/
│       └── tracing.py           # New: setup_tracing(), get_tracer() helpers
├── infrastructure/services/
│   ├── langchain_agent_service.py   # Add manual spans
│   └── openai_tagging_service.py    # Add manual spans
main.py                              # Call setup_tracing() in lifespan startup
docker-compose.yml                   # Add jaeger service
```

### Pattern 1: TracerProvider Initialization in Lifespan

**What:** Initialize the TracerProvider once at app startup in the FastAPI `lifespan` context manager, before `FastAPIInstrumentor.instrument_app()` is called.

**When to use:** Always. Module-level initialization breaks with uvicorn `--reload` (creates child processes; OTEL state is initialized in parent and not cleanly replicated). The `lifespan` approach is safe.

**Example:**
```python
# src/infrastructure/telemetry/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION

def setup_tracing(
    service_name: str,
    service_version: str,
    environment: str,
    otlp_endpoint: str,
    enabled: bool = True,
) -> None:
    if not enabled:
        return

    resource = Resource.create(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": environment,
    })

    exporter = OTLPSpanExporter(
        endpoint=f"{otlp_endpoint}/v1/traces",  # e.g. http://jaeger:4318/v1/traces
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)


def get_tracer(name: str) -> trace.Tracer:
    return trace.get_tracer(name)
```

```python
# main.py lifespan — call BEFORE FastAPIInstrumentor
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing(
        service_name=settings.app_name,
        service_version=settings.version,
        environment=settings.environment,
        otlp_endpoint=settings.otel_endpoint,
        enabled=settings.otel_enabled,
    )
    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="health,metrics",
    )
    # ... rest of startup
    yield
    # Shutdown: flush spans
    trace.get_tracer_provider().shutdown()
```

### Pattern 2: Manual Spans with `start_as_current_span` (async-safe)

**What:** Wrap key async methods with a context manager span. Python 3.11 `contextvars` propagates context correctly to awaited coroutines.

**When to use:** Any async method where you want named timing in the trace — LangChainAgentService, OpenAITaggingService.

**Key rule:** Use `with tracer.start_as_current_span(...)` as a context manager inside the `async def` body. Do NOT use `@tracer.start_as_current_span` as a decorator on async functions — the decorator form had a bug (incorrect 0s timing) that was fixed in PR #3633 but using the context manager is unambiguous and always correct.

**Example:**
```python
# Source: https://opentelemetry.io/docs/languages/python/instrumentation/
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class LangChainAgentService(IAgentService):
    async def send_message(self, user_id, agent_type, message, context):
        with tracer.start_as_current_span("emotionai.chat.generate") as span:
            span.set_attribute("user.id", str(user_id))
            span.set_attribute("agent.type", agent_type)
            span.set_attribute("message.length", len(message))
            try:
                # ... existing code ...
                result = await self.llm_service.generate_therapy_response(...)
                span.set_attribute("crisis_detected", result.crisis_detected)
                return result
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
```

### Pattern 3: Nested Spans for Sub-operations

**What:** Create child spans for sub-steps within a parent span. Context propagation is automatic — the child span's parent is the currently active span.

**When to use:** Inside `send_message`, wrap `_build_agent_context`, `_get_or_create_conversation`, and LLM calls separately to see timing breakdown.

**Example:**
```python
async def send_message(self, user_id, agent_type, message, context):
    with tracer.start_as_current_span("emotionai.chat.generate") as root_span:
        # Child span 1 — conversation lookup
        with tracer.start_as_current_span("emotionai.chat.get_conversation"):
            conversation_id = await self._get_or_create_conversation(user_id, agent_type)

        # Child span 2 — context building (makes LLM call internally)
        with tracer.start_as_current_span("emotionai.chat.build_context"):
            agent_context = await self._build_agent_context(...)

        # Child span 3 — actual LLM generation
        with tracer.start_as_current_span("emotionai.chat.llm_generate"):
            therapy_response = await self.llm_service.generate_therapy_response(...)
```

### Pattern 4: Async Task Context Propagation (asyncio.create_task)

**What:** When spawning `asyncio.create_task()`, context is only inherited if the task is created INSIDE an active span.

**When to use:** Only if fire-and-forget tasks are spawned within a traced method. LangChainAgentService currently uses `await` everywhere (no fire-and-forget), so this pattern is not immediately needed. Document for completeness.

**Example:**
```python
# WRONG — task created outside span, context is lost
async def bad_pattern():
    task = asyncio.create_task(some_work())
    with tracer.start_as_current_span("my_span"):
        await task

# CORRECT — task created inside span, context is inherited
async def good_pattern():
    with tracer.start_as_current_span("my_span"):
        task = asyncio.create_task(some_work())  # inside span = context copied
        await task
```

### Anti-Patterns to Avoid

- **Module-level TracerProvider init:** Breaks with uvicorn `--reload` because child processes don't cleanly inherit OTEL state. Always initialize in `lifespan` startup.
- **`@tracer.start_as_current_span` decorator on async functions:** Historical bug (fixed in PR #3633) caused 0s span duration. Use the context manager `with tracer.start_as_current_span(...)` form inside the function body instead.
- **Instrumenting before setting TraceProvider:** `FastAPIInstrumentor.instrument_app()` must be called AFTER `trace.set_tracer_provider(provider)` — otherwise it registers a no-op tracer.
- **Swallowing exceptions without recording them:** Always call `span.record_exception(e)` and `span.set_status(ERROR)` in except blocks, then re-raise. Silent exceptions produce deceptive "OK" spans.
- **Missing `/v1/traces` suffix:** The OTLPSpanExporter endpoint must be `http://jaeger:4318/v1/traces` — the exporter does NOT append the path automatically.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP span capture on FastAPI routes | Custom middleware timing requests | `opentelemetry-instrumentation-fastapi` | Handles ASGI lifecycle, span naming, HTTP status codes, W3C trace context header extraction/injection |
| DB query tracing | Manual timing around SQLAlchemy calls | `opentelemetry-instrumentation-asyncpg` | Instruments at driver level — captures actual SQL text, latency, connection pool events |
| Outbound HTTP to OpenAI | Custom httpx event hooks | `opentelemetry-instrumentation-httpx` | Auto-injects traceparent headers into outbound requests, captures response status |
| Trace context propagation across async | Manual `contextvars` management | Python `contextvars` + OTEL's built-in propagation | OTEL SDK already uses `contextvars` internally; `with tracer.start_as_current_span()` sets context automatically |
| Trace ID generation | UUID generation | OTEL SDK's `generate_span_id()` / `generate_trace_id()` | W3C Trace Context format (128-bit trace ID, 64-bit span ID) — tools expect this format |

**Key insight:** The OTEL SDK handles trace context propagation, W3C header injection/extraction, span ID generation, batching, and retry-on-failure export. Manual implementations miss retry logic, backpressure, and spec compliance.

---

## Common Pitfalls

### Pitfall 1: `--reload` Breaks Instrumentation
**What goes wrong:** Running uvicorn with `--reload=True` (the docker-compose dev setup) causes the TracerProvider to be initialized in the file-watcher parent process. On reload, the subprocess does not cleanly inherit the OTEL state. Spans may export to a stale exporter or not export at all.

**Why it happens:** uvicorn `--reload` uses subprocess forking. The OTEL SDK holds file descriptors and context state that don't transfer cleanly.

**How to avoid:** In `docker-compose.yml`, set `ENVIRONMENT=development` and keep `reload=True` for the API service, BUT initialize the TracerProvider inside the `lifespan` function (not at module level). This re-initializes OTEL correctly on each worker restart.

**Warning signs:** Spans appear in logs (`ConsoleSpanExporter` for debug) but never reach Jaeger. Span timestamps show epoch 0.

### Pitfall 2: Missing `/v1/traces` in OTLP HTTP Endpoint
**What goes wrong:** `OTLPSpanExporter(endpoint="http://jaeger:4318")` silently fails — no error, no spans in Jaeger.

**Why it happens:** The OTLP HTTP exporter requires the full path. Port 4318 is the OTLP receiver port; `/v1/traces` is the specific endpoint for trace data.

**How to avoid:** Always use the full path: `endpoint="http://jaeger:4318/v1/traces"`.

**Warning signs:** Spans are created (visible via `ConsoleSpanExporter`) but Jaeger UI shows 0 services.

### Pitfall 3: AsyncPG Spans Not Appearing (Wrong Instrumentor)
**What goes wrong:** Using `SQLAlchemyInstrumentor` with an async engine produces no DB spans in Jaeger.

**Why it happens:** The SQLAlchemy instrumentor was built for sync engines. When using `create_async_engine` with asyncpg, the instrumentation hooks don't fire for async operations without `engine.sync_engine`.

**How to avoid:** Use `AsyncPGInstrumentor().instrument()` for asyncpg-backed engines. Call it before creating any asyncpg connections (before the container initializes the engine).

**Warning signs:** FastAPI HTTP spans appear in Jaeger, but there are no child DB spans.

### Pitfall 4: Span Exporter Not Flushing on Shutdown
**What goes wrong:** The last N spans before process exit are lost — spans are still in the `BatchSpanProcessor` buffer when the process exits.

**Why it happens:** `BatchSpanProcessor` exports asynchronously. If the process exits before the export timer fires, buffered spans are dropped.

**How to avoid:** In the `lifespan` shutdown phase, call `trace.get_tracer_provider().shutdown()`. This flushes all pending spans synchronously before exit.

**Warning signs:** Trace for the last few requests before docker-compose down is missing final spans.

### Pitfall 5: LangChain Auto-Instrumentor Will Not Trace EmotionAI's Agent
**What goes wrong:** Installing `opentelemetry-instrumentation-langchain` and calling `LangchainInstrumentor().instrument()` produces no LangChain-related spans in Jaeger for EmotionAI.

**Why it happens:** The LangChain instrumentor patches LangChain's LCEL chain objects (`.invoke()`, `.ainvoke()`). EmotionAI's `LangChainAgentService` wraps a custom `ILLMService` interface — it never calls LangChain chain methods directly, so there are no hooks to patch.

**How to avoid:** Use manual spans inside `LangChainAgentService` and `OpenAITaggingService`. Manual spans are the correct and only approach here.

**Warning signs:** `LangchainInstrumentor().instrument()` completes without error, but no `langchain.*` spans appear.

---

## Code Examples

Verified patterns from official sources:

### Full TracerProvider Setup (OTLP HTTP)
```python
# src/infrastructure/telemetry/tracing.py
# Source: https://opentelemetry.io/docs/languages/python/exporters/
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def setup_tracing(service_name: str, service_version: str,
                  environment: str, otlp_endpoint: str, enabled: bool = True) -> None:
    if not enabled:
        return

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": environment,
    })

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        )
    )
    trace.set_tracer_provider(provider)

    # Instrument asyncpg BEFORE any connections are created
    AsyncPGInstrumentor().instrument()
    # Instrument all httpx clients (catches OpenAI SDK calls)
    HTTPXClientInstrumentor().instrument()
```

### FastAPIInstrumentor Call (in lifespan)
```python
# main.py — inside lifespan(), after setup_tracing()
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor.instrument_app(
    app,
    excluded_urls="health,/health/",  # Don't trace health checks
)
```

### Manual Spans in LangChainAgentService
```python
# src/infrastructure/services/langchain_agent_service.py
# Source: https://opentelemetry.io/docs/languages/python/instrumentation/
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class LangChainAgentService(IAgentService):

    async def send_message(self, user_id, agent_type, message, context):
        with tracer.start_as_current_span("emotionai.chat.generate") as span:
            span.set_attribute("user.id", str(user_id))
            span.set_attribute("agent.type", agent_type)
            span.set_attribute("message.char_count", len(message))
            try:
                with tracer.start_as_current_span("emotionai.chat.get_conversation"):
                    conversation_id = await self._get_or_create_conversation(user_id, agent_type)

                with tracer.start_as_current_span("emotionai.chat.build_context") as ctx_span:
                    agent_context = await self._build_agent_context(
                        user_id, agent_type, conversation_id, message
                    )
                    ctx_span.set_attribute("context.message_count",
                                           len(agent_context.recent_messages))

                with tracer.start_as_current_span("emotionai.chat.llm_generate") as llm_span:
                    therapy_response = await self.llm_service.generate_therapy_response(
                        agent_context, message
                    )
                    llm_span.set_attribute("crisis_detected", therapy_response.crisis_detected)
                    llm_span.set_attribute("therapeutic_approach",
                                           therapy_response.therapeutic_approach)

                span.set_attribute("crisis_detected", therapy_response.crisis_detected)
                return therapy_response

            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
```

### Manual Spans in OpenAITaggingService
```python
# src/infrastructure/services/openai_tagging_service.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class OpenAITaggingService(ITaggingService):

    async def extract_tags_from_message(self, content, user_context=None):
        with tracer.start_as_current_span("emotionai.tagging.classify") as span:
            span.set_attribute("tagging.content_length", len(content))
            span.set_attribute("tagging.model", self.model)
            try:
                result = await self.client.chat.completions.create(...)
                span.set_attribute("tagging.tag_count", len(result_data.get("tags", [])))
                span.set_attribute("tagging.confidence", result_data.get("confidence", 0))
                return TagExtractionResult(...)
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
```

### Jaeger docker-compose service
```yaml
# docker-compose.yml addition
jaeger:
  image: jaegertracing/all-in-one:1.76.0
  ports:
    - "16686:16686"   # Jaeger UI
    - "4318:4318"     # OTLP HTTP receiver
  environment:
    - COLLECTOR_OTLP_ENABLED=true
  networks:
    - emotionai-network
```

> Note: In Jaeger 1.35+, port 4318 (OTLP HTTP) is enabled by default. `COLLECTOR_OTLP_ENABLED=true` is included defensively for compatibility with any version of the image.

### Settings additions
```python
# src/infrastructure/config/settings.py — add to Settings class
# Observability — OpenTelemetry
otel_enabled: bool = Field(default=True, env="OTEL_ENABLED")
otel_endpoint: str = Field(default="http://jaeger:4318", env="OTEL_EXPORTER_OTLP_ENDPOINT")
otel_service_name: str = Field(default="emotionai-api", env="OTEL_SERVICE_NAME")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Vendor SDKs (Datadog, New Relic agents) | OpenTelemetry SDK + any backend | 2021 (OTEL GA) | Switch backends without code changes; use Jaeger now, Grafana Tempo later |
| Zipkin B3 propagation headers | W3C Trace Context (`traceparent`) | OTEL 1.0 (2021) | Standard header works across all OTEL-compliant tools |
| Jaeger Agent UDP on port 6831 | OTLP HTTP/gRPC direct to Collector | Jaeger 1.35+ (2022) | Simpler — no agent sidecar needed; one port |
| `COLLECTOR_OTLP_ENABLED=true` required | OTLP enabled by default in Jaeger | Jaeger 1.35+ | Still safe to include for compatibility |
| `@tracer.start_as_current_span` decorator on async | `with tracer.start_as_current_span()` context manager | OTEL Python SDK PR #3633 | Decorator now works but context manager is clearer |

**Deprecated/outdated:**
- Jaeger UDP ports (6831, 6832): superseded by OTLP; exclude from docker-compose
- Zipkin port (9411): not needed for this setup
- `jaegertracing/all-in-one:latest`: pin to `1.76.0` to avoid breaking image changes
- `opentelemetry-exporter-jaeger`: the dedicated Jaeger exporter package is deprecated; use OTLP exporter instead

---

## Open Questions

1. **Does `opentelemetry-instrumentation-httpx` correctly capture OpenAI SDK calls?**
   - What we know: the OpenAI Python SDK uses `httpx` as its HTTP client. `HTTPXClientInstrumentor` patches all httpx client instances.
   - What's unclear: whether the OpenAI SDK creates its httpx client before or after `HTTPXClientInstrumentor().instrument()` is called. If the client is created at import time (module level), the patching may miss it.
   - Recommendation: Verify during Wave 1 by checking whether `POST https://api.openai.com/v1/chat/completions` spans appear as children of the `emotionai.chat.llm_generate` span. If not, add a manual span for the OpenAI call directly.

2. **AsyncPGInstrumentor timing relative to container engine creation**
   - What we know: `AsyncPGInstrumentor().instrument()` must be called before any asyncpg connections are made. The `ApplicationContainer` creates the SQLAlchemy async engine during `initialize_container()`.
   - What's unclear: whether the asyncpg connections are created at engine creation time or lazily on first query.
   - Recommendation: Call `AsyncPGInstrumentor().instrument()` in `setup_tracing()`, which runs before `initialize_container()` in the lifespan. This ensures instrumentation is in place before any connections are made.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4+, asyncio_mode=auto |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/ -q` |
| Full suite command | `pytest tests/ --cov=src --cov-report=term-missing` |

### Phase Requirements → Test Map

The nature of tracing means most validation is observational (check Jaeger UI) rather than unit-testable. The following maps what CAN be tested automatically vs what requires manual verification.

| Req | Behavior | Test Type | Automated Command | Notes |
|-----|----------|-----------|-------------------|-------|
| OTEL-01 | TracerProvider initializes without error | unit | `pytest tests/unit/test_tracing_setup.py -x` | Wave 0 — mock OTLPSpanExporter |
| OTEL-02 | `setup_tracing(enabled=False)` is a no-op | unit | `pytest tests/unit/test_tracing_setup.py::test_tracing_disabled -x` | Verifies dev can disable OTEL |
| OTEL-03 | LangChainAgentService creates spans | unit | `pytest tests/unit/test_langchain_spans.py -x` | Use `InMemorySpanExporter` to capture spans |
| OTEL-04 | OpenAITaggingService creates spans | unit | `pytest tests/unit/test_tagging_spans.py -x` | Use `InMemorySpanExporter` |
| OTEL-05 | Spans appear in Jaeger at localhost:16686 | smoke/manual | `docker-compose up && curl -s http://localhost:8000/health` then check UI | Cannot automate Jaeger UI check |
| OTEL-06 | Trace shows FastAPI → LangChain → OpenAI parent/child hierarchy | smoke/manual | Hit `POST /v1/api/chat` and inspect trace in Jaeger UI | Requires running stack |

### Unit Test Approach: InMemorySpanExporter

The key technique for automated span testing is `InMemorySpanExporter` from the OTEL SDK — it captures spans in memory without sending them to Jaeger:

```python
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

def setup_test_tracer():
    """Returns (tracer_provider, span_exporter) for test assertions."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter

# In test:
def test_send_message_creates_chat_span():
    provider, exporter = setup_test_tracer()
    trace.set_tracer_provider(provider)

    service = LangChainAgentService(...)
    await service.send_message(...)

    spans = exporter.get_finished_spans()
    span_names = [s.name for s in spans]
    assert "emotionai.chat.generate" in span_names
    root = next(s for s in spans if s.name == "emotionai.chat.generate")
    assert root.status.status_code == StatusCode.OK
```

### Sampling Rate
- **Per task commit:** `pytest tests/ -q` (all existing tests — confirm no regressions)
- **Per wave merge:** `pytest tests/ --cov=src --cov-report=term-missing`
- **Phase gate:** Full suite green + manual Jaeger smoke test (`docker-compose up`, hit chat endpoint, verify trace in UI)

### Wave 0 Gaps
- [ ] `tests/unit/test_tracing_setup.py` — covers OTEL-01, OTEL-02
- [ ] `tests/unit/test_langchain_spans.py` — covers OTEL-03
- [ ] `tests/unit/test_tagging_spans.py` — covers OTEL-04
- [ ] `src/infrastructure/telemetry/__init__.py` — new package, needs `__init__.py`
- [ ] `src/infrastructure/telemetry/tracing.py` — new file
- [ ] Package installs: `pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp-proto-http opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-asyncpg opentelemetry-instrumentation-httpx`

---

## Learning Doc Outline (docs/learning/opentelemetry.md)

The learning doc must use the actual EmotionAI trace as the worked example. Required sections per ROADMAP.md:

1. **What is it and why do we use it here** — The three pillars (traces, metrics, logs). Why traces are the right tool for diagnosing LLM latency. Why OTEL beats vendor SDKs (portability, no lock-in).
2. **How it works conceptually** — Span anatomy (trace ID, span ID, parent span ID, name, attributes, status, events). Context propagation via `contextvars`. The TracerProvider → Tracer → Span hierarchy. BatchSpanProcessor buffering. OTLP as the wire protocol.
3. **Key patterns used in this project** — Walk through the actual EmotionAI trace: HTTP request → `emotionai.chat.generate` → `emotionai.chat.build_context` → `emotionai.chat.llm_generate` → asyncpg DB span + httpx OpenAI span. Show the Jaeger UI screenshot equivalent.
4. **Common mistakes and how to avoid them** — The five pitfalls from this research doc.
5. **Further reading** — OTEL Python docs, OpenTelemetry specification, W3C Trace Context spec.

---

## Sources

### Primary (HIGH confidence)
- [opentelemetry-python-contrib FastAPI instrumentation docs](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html) — FastAPIInstrumentor API, excluded_urls, hooks
- [opentelemetry.io Python exporters](https://opentelemetry.io/docs/languages/python/exporters/) — OTLP HTTP exporter setup
- [opentelemetry.io Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/) — span creation patterns
- [Jaeger getting-started docs v1.76](https://www.jaegertracing.io/docs/1.76/getting-started/) — confirmed port 4318 OTLP HTTP, port 16686 UI, no extra env var needed
- [PyPI: opentelemetry-instrumentation-asyncpg](https://pypi.org/project/opentelemetry-instrumentation-asyncpg/) — v0.61b0, Python >=3.9, active

### Secondary (MEDIUM confidence)
- [PyPI: opentelemetry-instrumentation-langchain](https://pypi.org/project/opentelemetry-instrumentation-langchain/) — v0.52.5 (Feb 2026); Traceloop/OpenLLMetry package; confirmed OTLP-compatible, not LangSmith-only
- [GitHub: open-telemetry/opentelemetry-python issue #3270](https://github.com/open-telemetry/opentelemetry-python/issues/3270) — decorator vs context manager for async functions; confirmed fixed via PR #3633
- [oneuptime.com: Fix Python asyncio context loss](https://oneuptime.com/blog/post/2026-02-06-fix-python-asyncio-context-loss/view) — asyncio.create_task() context propagation fix patterns; cross-verified with OTEL docs

### Tertiary (LOW confidence — flag for validation)
- [oneuptime.com: Instrument async SQLAlchemy 2.0](https://oneuptime.com/blog/post/2026-02-06-instrument-async-sqlalchemy-2-opentelemetry/view) — `engine.sync_engine` trick; single source, use `AsyncPGInstrumentor` instead
- SigNoz article on `--reload` breaking instrumentation — single blog source but confirmed by OTEL troubleshooting docs reference

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages confirmed on PyPI with recent versions; OTLP HTTP approach confirmed in official Jaeger docs
- Architecture patterns: HIGH — initialization order, context manager vs decorator, lifespan placement all verified against official OTEL Python docs and confirmed bug reports
- LangChain instrumentor limitation: HIGH — code inspection of LangChainAgentService confirms it wraps ILLMService, not LangChain chain objects directly
- Pitfalls: MEDIUM-HIGH — reload/endpoint/asyncpg pitfalls verified; OpenAI httpx instrumentation timing is LOW (single open question)

**Research date:** 2026-03-19
**Valid until:** 2026-06-19 (OTEL Python SDK is relatively stable; LangChain instrumentor moves fast — re-verify version compatibility before implementation)
