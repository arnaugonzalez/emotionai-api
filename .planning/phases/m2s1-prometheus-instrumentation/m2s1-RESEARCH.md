# Phase m2s1: Prometheus Instrumentation — Research

**Researched:** 2026-03-19
**Domain:** Prometheus metrics, prometheus-fastapi-instrumentator, Grafana, docker-compose observability
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use `prometheus-fastapi-instrumentator` (specified in roadmap — not negotiable)
- Custom metric names: `emotionai_chat_requests_total`, `emotionai_active_users_gauge`, `emotionai_openai_latency_seconds`
- Prometheus + Grafana in docker-compose
- Write `docs/learning/prometheus_fastapi.md`
- Three deliverables: `/metrics` endpoint, 3 custom business metrics, learning doc

### Claude's Discretion
- Exact Grafana dashboard JSON structure (keep minimal: request rate + latency)
- Whether to add alert rules (deferred — keep scope tight)
- Custom metric label cardinality (avoid high-cardinality labels like user_id)

### Deferred Ideas (OUT OF SCOPE)
- Prometheus alerting rules (alertmanager setup)
- Long-term metric storage (Thanos, Cortex)
- Custom collector for DB connection pool metrics
</user_constraints>

---

## Summary

`prometheus-fastapi-instrumentator` v7.1.0 is a thin wrapper around `prometheus_client` that wires into FastAPI with three lines of code, exposes a `/metrics` endpoint, and auto-instruments every route with request count, latency histogram, and request/response size summaries. It is the correct library for this project.

The main wiring concern in EmotionAI is **middleware ordering**. `main.py` already has three `BaseHTTPMiddleware` classes (`LoggingMiddleware`, `ErrorHandlingMiddleware`, `RateLimitingMiddleware`). These must all be added with `app.add_middleware()` before `Instrumentator().instrument(app)` is called, and `.expose(app)` must be called inside the lifespan context manager to be compatible with FastAPI's modern lifespan pattern. Calling `.expose()` at module level (outside lifespan) causes the `/metrics` route to be registered before the app is fully configured.

For the docker-compose setup, Prometheus + Grafana add two services, a `monitoring` network shared with the `api` service, and a `prometheus/prometheus.yml` config file. Because the API runs in the same docker-compose network, Prometheus reaches it at `api:8000` (not `host.docker.internal`). Grafana is pre-provisioned with a datasource pointing to `http://prometheus:9090` so no manual UI setup is needed.

**Primary recommendation:** Wire `Instrumentator` in `create_application()` after all `add_middleware()` calls; call `.expose()` inside the `lifespan` startup block.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| prometheus-fastapi-instrumentator | 7.1.0 | Auto-instrument FastAPI + expose `/metrics` | Purpose-built for FastAPI/Starlette; 3-line integration; wraps prometheus_client |
| prometheus_client | (transitive dep) | Counter/Gauge/Histogram primitives for custom metrics | Official Python client by Prometheus project |
| prom/prometheus | v2.40+ (Docker image) | Scrape + store metrics time-series | Industry standard; native PromQL |
| grafana/grafana | 10.x (Docker image) | Dashboard + visualization | Standard companion to Prometheus |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| prometheus_client (direct import) | same as above | Define custom metrics (Counter, Gauge, Histogram) at module level | Any custom business metric beyond what instrumentator auto-provides |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| prometheus-fastapi-instrumentator | opentelemetry-sdk metrics | OTEL is planned for slice 2.3 — don't add it here, creates confusion |
| prometheus-fastapi-instrumentator | prometheus_client directly | More code, no auto-route instrumentation |
| Grafana datasource provisioning | Manual Grafana UI setup | Provisioning survives container restarts; no manual steps |

**Installation:**
```bash
pip install prometheus-fastapi-instrumentator==7.1.0
```

Add to `requirements.txt`:
```
prometheus-fastapi-instrumentator>=7.1.0
```

---

## Architecture Patterns

### Recommended Project Structure

New files this slice adds:

```
emotionai-api/
├── main.py                          # Modified: instrument + expose Prometheus
├── requirements.txt                 # Add prometheus-fastapi-instrumentator
├── src/
│   └── infrastructure/
│       └── metrics/
│           ├── __init__.py
│           └── custom_metrics.py    # Counter, Gauge, Histogram definitions
├── prometheus/
│   └── prometheus.yml               # Scrape config
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml       # Auto-provision Prometheus datasource
│       └── dashboards/
│           ├── dashboards.yml       # Dashboard provider config
│           └── emotionai.json       # Dashboard definition
├── docker-compose.yml               # Add prometheus + grafana services
└── docs/
    └── learning/
        └── prometheus_fastapi.md    # Learning doc
```

### Pattern 1: Instrumentator wiring with lifespan

**What:** Wire the instrumentator in `create_application()` AFTER all middleware is registered. Expose the endpoint inside the existing `lifespan` async context manager.

**When to use:** Any FastAPI app using the modern `lifespan=` parameter (not deprecated `@on_event`). EmotionAI already uses lifespan.

**Why this ordering matters:** `app.add_middleware()` wraps the app in Starlette's middleware stack. The instrumentator hooks into the ASGI app to intercept requests. If `.instrument(app)` is called before middleware is added, those middleware layers are not instrumented. If `.expose(app)` is called at module level, the route is registered before the lifespan fires — this works but is less clean and can conflict with the `redirect_slashes=False` setting.

```python
# Source: https://github.com/trallnag/prometheus-fastapi-instrumentator
# In main.py — create_application()

from prometheus_fastapi_instrumentator import Instrumentator

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
        redirect_slashes=False,
        ...
    )

    # STEP 1: All middleware first
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RateLimitingMiddleware, ...)

    # STEP 2: Instrument AFTER middleware (but before expose)
    # Store on app.state so lifespan can call .expose()
    app.state.instrumentator = (
        Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/metrics", "/health/"],
        )
        .instrument(app)
    )

    # STEP 3: Include routers
    app.include_router(health_router, ...)
    ...
    return app


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    container = await initialize_container(settings.__dict__)
    app.state.container = container

    # Expose /metrics here — after app is fully configured
    app.state.instrumentator.expose(
        app,
        include_in_schema=False,
    )

    yield

    # Shutdown
    await shutdown_container()
```

### Pattern 2: Custom metrics at module level

**What:** Define `Counter`, `Gauge`, `Histogram` at import time in a dedicated `metrics/custom_metrics.py` module. Import and use them from routers.

**When to use:** All custom business metrics. Never define them inside route handlers (creates new metric objects on every request — crashes with "Duplicated timeseries" error).

```python
# Source: https://prometheus.github.io/client_python/
# src/infrastructure/metrics/custom_metrics.py

from prometheus_client import Counter, Gauge, Histogram

# Counter — only ever increases; reset to zero on process restart
# Use for: completed events (requests, errors, logins)
chat_requests_total = Counter(
    name="emotionai_chat_requests_total",
    documentation="Total number of chat API requests",
    labelnames=["agent_type", "status"],
    # GOOD labels: agent_type has 2 values (therapy, wellness), status has 3 (success, error, crisis)
    # BAD label: user_id — would create unbounded time series
)

# Gauge — can go up and down; represents current state
# Use for: in-flight requests, active sessions, queue depth
active_users_gauge = Gauge(
    name="emotionai_active_users_gauge",
    documentation="Number of users with an active chat session in the last 5 minutes",
)

# Histogram — samples observations into buckets for percentile analysis
# Use for: latency, request sizes
# Buckets chosen to capture typical OpenAI latency range (100ms – 30s)
openai_latency_seconds = Histogram(
    name="emotionai_openai_latency_seconds",
    documentation="Latency of OpenAI API calls in seconds",
    labelnames=["call_type"],  # e.g., "chat_completion", "tagging"
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
```

Usage in `chat.py` router:

```python
# src/presentation/api/routers/chat.py
import time
from src.infrastructure.metrics.custom_metrics import (
    chat_requests_total,
    openai_latency_seconds,
)

@router.post("/chat", ...)
async def chat_with_agent(...):
    start = time.perf_counter()
    try:
        response = await chat_use_case.execute(...)
        crisis = getattr(response, 'crisis_detected', False)
        status_label = "crisis" if crisis else "success"
        chat_requests_total.labels(agent_type=payload.agent_type, status=status_label).inc()
        openai_latency_seconds.labels(call_type="chat_completion").observe(
            time.perf_counter() - start
        )
        return api_response
    except Exception:
        chat_requests_total.labels(agent_type=payload.agent_type, status="error").inc()
        raise
```

### Pattern 3: Grafana datasource provisioning

**What:** Place a `datasources/prometheus.yml` file in `grafana/provisioning/` so Grafana auto-connects to Prometheus on first start. No clicking in the UI.

```yaml
# grafana/provisioning/datasources/prometheus.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false
```

### Pattern 4: docker-compose integration

**What:** Add `prometheus` and `grafana` services to the existing `docker-compose.yml`. Both services join `emotionai-network` to reach the `api` service by its container name.

**Key insight for EmotionAI:** Prometheus scrapes `api:8000` (the docker-compose service name), NOT `host.docker.internal`. The `api` service already runs on the `emotionai-network`.

```yaml
# Addition to docker-compose.yml

  prometheus:
    image: prom/prometheus:v2.50.0
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    networks:
      - emotionai-network
    depends_on:
      - api

  grafana:
    image: grafana/grafana:10.4.0
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    ports:
      - "3000:3000"
    networks:
      - emotionai-network
    depends_on:
      - prometheus
```

```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'emotionai-api'
    scrape_interval: 10s
    metrics_path: '/metrics'
    static_configs:
      - targets: ['api:8000']
        labels:
          environment: 'development'
```

### Anti-Patterns to Avoid

- **Defining metrics inside route handlers:** Creates a new `Counter` object on every request. Crashes with `ValueError: Duplicated timeseries` on the second request. Always define at module level.
- **High-cardinality labels:** Do NOT use `user_id`, `request_id`, or `ip_address` as label values. Each unique value creates a new time series. 1000 users = 1000 time series for one metric.
- **Calling `.expose()` before middleware is added:** Registers the `/metrics` route, then middleware wraps the app — `/metrics` requests get rate-limited and logged unnecessarily. Call expose after setup.
- **Scraping `/metrics` from within the app's own rate limiter:** The `RateLimitingMiddleware` in `rate_limiting.py` already skips `/health/`. Add a similar skip for `/metrics` if rate limits are low, or use `excluded_handlers=["/metrics"]` in the Instrumentator config to prevent instrumentating the metrics endpoint itself.
- **Using `should_respect_env_var=True` without setting the env var:** Silently disables all instrumentation. Easy to miss.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP request count per route | Custom request counting middleware | Instrumentator auto-instrumentation | Handles templated vs untemplated routes, status code grouping, error tracking |
| Request latency histogram | Manual `time.time()` in every route | Instrumentator `http_request_duration_seconds` | Gets buckets right, handles streaming correctly |
| `/metrics` endpoint | Custom route returning text | `instrumentator.expose(app)` | Handles content negotiation, gzip, Prometheus text format spec |
| Metric text format serialization | Manual `text/plain; version=0.0.4` | `prometheus_client` internals | The format has edge cases (escaping, newlines, timestamp precision) |

**Key insight:** The auto-instrumentation covers 80% of what you need. Custom metrics are only needed for business-level signals (e.g., "how many crisis detections happened") that HTTP request data can't tell you.

---

## Common Pitfalls

### Pitfall 1: "Duplicated timeseries" ValueError on startup or reload

**What goes wrong:** `ValueError: Duplicated timeseries in CollectorRegistry` crash on startup, usually on the second `docker-compose up` or when uvicorn hot-reloads.

**Why it happens:** Custom metrics defined at module level are registered in the global `CollectorRegistry`. If the module is imported twice in the same process (e.g., `--reload` mode importing `main.py` twice), the second registration raises an error.

**How to avoid:** Use `prometheus_client.REGISTRY.unregister()` defensively, or use the `registry=` parameter on each metric:
```python
try:
    chat_requests_total = Counter("emotionai_chat_requests_total", ...)
except ValueError:
    # Already registered — retrieve existing metric
    chat_requests_total = REGISTRY._names_to_collectors["emotionai_chat_requests_total"]
```
A cleaner approach: guard with a module-level singleton (define in one file, import everywhere).

**Warning signs:** Crash on second startup or `--reload`. Works fine on first `docker-compose up`, fails on second.

### Pitfall 2: `/metrics` blocked by rate limiter

**What goes wrong:** Prometheus cannot scrape `/metrics` because `RateLimitingMiddleware` counts scrapes against the Prometheus server's IP quota (15s scrape interval = 4 req/min, fine; but if rate limit is 60/min and there are other requests from same IP this may be a non-issue).

**Why it happens:** `RateLimitingMiddleware` only exempts paths starting with `/health`. Prometheus scraper has one IP; all its scrapes count.

**How to avoid:** Add `/metrics` to the skip list in `RateLimitingMiddleware.dispatch()`:
```python
if request.url.path.startswith("/health") or request.url.path == "/metrics":
    return await call_next(request)
```

**Warning signs:** Prometheus shows `context deadline exceeded` or 429 errors in scrape logs.

### Pitfall 3: Multiprocess mode needed with multiple uvicorn workers

**What goes wrong:** With `workers=4` (production config in `main.py`), each worker maintains its own in-memory metric registry. The `/metrics` endpoint from worker 1 only sees worker 1's counters, not the total.

**Why it happens:** `prometheus_client` stores metrics in process memory by default.

**How to avoid:** Set `PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc` in environment. The client library automatically switches modes. This is only needed in production with multiple workers; the docker-compose dev setup uses a single uvicorn process.

**Warning signs:** Inconsistent metric values on repeated scrapes; total request count doesn't match nginx access logs.

### Pitfall 4: Histogram buckets not covering actual latency range

**What goes wrong:** OpenAI calls take 2–15 seconds; if all buckets are below 2 seconds, all observations fall in the `+Inf` bucket and percentiles are useless.

**Why it happens:** Default instrumentator buckets are optimized for fast HTTP responses (ms range), not LLM calls.

**How to avoid:** Specify custom buckets for `emotionai_openai_latency_seconds`:
```python
buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
```

**Warning signs:** PromQL `histogram_quantile(0.95, ...)` returns `+Inf` for the OpenAI metric.

### Pitfall 5: Container networking — Prometheus can't reach the API

**What goes wrong:** Prometheus shows `connection refused` when scraping `api:8000` inside docker-compose.

**Why it happens:** The `prometheus` service is on a different network than `api`, or the `api` service name is wrong in `prometheus.yml`.

**How to avoid:** Both services must be on the same docker-compose network (`emotionai-network`). The scrape target must use the docker-compose service name (`api`), not `localhost` or `127.0.0.1`.

**Warning signs:** Prometheus UI (`localhost:9090/targets`) shows target state as `DOWN`.

---

## Code Examples

### Full instrumentator wiring (verified pattern)

```python
# Source: https://github.com/trallnag/prometheus-fastapi-instrumentator v7.1.0
from prometheus_fastapi_instrumentator import Instrumentator

# In create_application() — after all add_middleware() calls
instrumentator = (
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/metrics", r"/health.*"],
    )
    .instrument(app)
)
app.state.instrumentator = instrumentator

# In lifespan() — expose the /metrics route
instrumentator.expose(app, include_in_schema=False)
```

### Custom Gauge with context manager (for active session tracking)

```python
# Source: https://prometheus.github.io/client_python/
from prometheus_client import Gauge

active_users_gauge = Gauge(
    "emotionai_active_users_gauge",
    "Active chat sessions in last 5 minutes",
)

# Option A: increment/decrement manually
active_users_gauge.inc()   # user starts session
active_users_gauge.dec()   # user ends session

# Option B: track_inprogress() context manager
with active_users_gauge.track_inprogress():
    # code that runs while session is active
    ...
```

### PromQL queries for Grafana dashboard

```promql
-- Request rate per endpoint (rate over 5m window)
rate(http_requests_total{job="emotionai-api"}[5m])

-- p95 latency per handler
histogram_quantile(0.95,
  sum(rate(http_request_duration_highr_seconds_bucket{job="emotionai-api"}[5m]))
  by (handler, le)
)

-- OpenAI p50 latency
histogram_quantile(0.50,
  rate(emotionai_openai_latency_seconds_bucket[5m])
  by (call_type, le)
)

-- Chat requests per minute, split by status
sum(rate(emotionai_chat_requests_total[1m])) by (status)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `lifespan=` async context manager | FastAPI 0.93 (2023) | `on_event` deprecated; use lifespan for expose() call |
| Prometheus native histograms (experimental) | Classic bucket histograms | v2.40+ (2022) | Native histograms more efficient but still experimental; use classic for compatibility |
| `should_respect_env_var` disabled by default | Still disabled by default | Stable | Good — dev setup always instruments without extra config |

**Deprecated/outdated:**
- `@app.on_event("startup")` for calling `instrumentator.expose()`: still works but deprecated since FastAPI 0.93. EmotionAI already uses `lifespan=` — stay consistent.
- `prometheus-fastapi-instrumentator` v5.x: had duplicated-metrics bugs fixed in v7. Use v7.1.0.

---

## Learning Doc Coverage Plan

The `docs/learning/prometheus_fastapi.md` must cover these concepts (per ROADMAP.md requirement and CONTEXT.md):

### Concept 1: What is observability and why metrics?
- Three pillars: logs (what happened), metrics (how much/how fast), traces (where time was spent)
- EmotionAI already has logs (`LoggingMiddleware`). Metrics answer "how many users are chatting right now?" and "what is the p95 latency of OpenAI calls?"

### Concept 2: Pull vs Push — why Prometheus pulls
- **Push model (StatsD, InfluxDB line protocol):** Application sends metrics to a central server. Simple for the app, but: fire-and-forget (you don't know if metrics arrived), tight coupling to the collector endpoint, hard to detect when an app goes silent (is it down, or just no traffic?).
- **Pull model (Prometheus):** Prometheus actively scrapes `/metrics` on a schedule. If the app doesn't respond, Prometheus marks it DOWN — you get an alert. The app doesn't need to know Prometheus's address. Multiple Prometheus servers can scrape the same app. Mental health context: "Is the app responding to users?" is answered automatically.
- **When push makes sense:** Short-lived processes (batch jobs) that might finish before Prometheus scrapes. Use `pushgateway` for those.

### Concept 3: Metric types
- **Counter:** `emotionai_chat_requests_total` — counts completed chat requests. PromQL `rate()` turns it into "requests per second." Never use for values that decrease.
- **Gauge:** `emotionai_active_users_gauge` — tracks current active sessions. Can go up and down. PromQL can use it directly: `emotionai_active_users_gauge > 100`.
- **Histogram:** `emotionai_openai_latency_seconds` — records each observation in pre-configured buckets. PromQL `histogram_quantile(0.95, ...)` gives the p95. Requires careful bucket selection (cover expected range, not too fine-grained).
- **Summary:** Similar to histogram but calculates quantiles client-side over a sliding window. Hard to aggregate across instances. Prefer histograms.

### Concept 4: Cardinality — the thing that kills Prometheus
- Every unique combination of label values = one time series.
- `emotionai_chat_requests_total{agent_type="therapy", status="success"}` = 1 series
- If you add `user_id` label: 1000 users × 2 agent_types × 3 statuses = 6000 series from one metric.
- Prometheus stores all time series in memory. High cardinality = OOM crash.
- Rule: labels must have bounded, low-count value sets.

### Concept 5: The `/metrics` text format
- Show a real example from EmotionAI's `/metrics` output and explain each line.
- Explain `# HELP`, `# TYPE`, metric lines, and label syntax.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.0 + pytest-asyncio (asyncio_mode=auto) |
| Config file | `pyproject.toml` |
| Quick run command | `pytest tests/ -q -x` |
| Full suite command | `pytest tests/ --cov=src --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| M2S1-01 | `GET /metrics` returns 200 with `Content-Type: text/plain` and Prometheus text format | integration | `pytest tests/integration/test_metrics.py -x` | Wave 0 |
| M2S1-02 | `/metrics` response contains `http_requests_total` after one API request | integration | `pytest tests/integration/test_metrics.py::test_metrics_contain_request_count -x` | Wave 0 |
| M2S1-03 | `emotionai_chat_requests_total` increments after a chat request | integration | `pytest tests/integration/test_metrics.py::test_chat_counter_increments -x` | Wave 0 |
| M2S1-04 | `emotionai_openai_latency_seconds` histogram buckets appear in `/metrics` | integration | `pytest tests/integration/test_metrics.py::test_openai_histogram_present -x` | Wave 0 |
| M2S1-05 | `emotionai_active_users_gauge` appears in `/metrics` output | integration | `pytest tests/integration/test_metrics.py::test_active_users_gauge_present -x` | Wave 0 |
| M2S1-06 | `/metrics` endpoint is excluded from rate limiting | integration | `pytest tests/integration/test_metrics.py::test_metrics_not_rate_limited -x` | Wave 0 |
| M2S1-07 | docker-compose `prometheus` service scrapes `api:8000/metrics` (manual) | smoke | `docker-compose up -d && curl localhost:9090/api/v1/targets` | manual |
| M2S1-08 | Grafana at `localhost:3000` shows Prometheus datasource connected (manual) | smoke | manual — check Grafana UI | manual |

### Key validation technique: how to test `/metrics` content

```python
# tests/integration/test_metrics.py
from fastapi.testclient import TestClient
from main import app

def test_metrics_endpoint_returns_prometheus_format():
    client = TestClient(app)
    # Make one request to populate counters
    client.get("/health/")
    # Now check metrics
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "# TYPE http_requests_total counter" in body
    assert "http_requests_total" in body

def test_custom_chat_counter_present():
    client = TestClient(app)
    response = client.get("/metrics")
    assert "emotionai_chat_requests_total" in response.text

def test_openai_histogram_buckets_present():
    client = TestClient(app)
    response = client.get("/metrics")
    assert "emotionai_openai_latency_seconds_bucket" in response.text
```

**Important test isolation issue:** `prometheus_client` uses a global `CollectorRegistry`. If tests share a process with a previously started app, custom metrics may already be registered. Use `pytest` with process isolation or handle the `ValueError: Duplicated timeseries` defensively in `custom_metrics.py`.

### Sampling Rate
- **Per task commit:** `pytest tests/integration/test_metrics.py -q -x`
- **Per wave merge:** `pytest tests/ --cov=src --cov-report=term-missing`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/integration/test_metrics.py` — covers M2S1-01 through M2S1-06
- [ ] `prometheus/prometheus.yml` — scrape config for docker-compose
- [ ] `grafana/provisioning/datasources/prometheus.yml` — auto-provision datasource
- [ ] `grafana/provisioning/dashboards/dashboards.yml` — dashboard provider config
- [ ] `grafana/provisioning/dashboards/emotionai.json` — minimal dashboard JSON
- [ ] `src/infrastructure/metrics/__init__.py` + `custom_metrics.py` — metric definitions
- [ ] `docs/learning/prometheus_fastapi.md` — learning doc stub

---

## Open Questions

1. **Registry isolation in tests with multiple workers**
   - What we know: `prometheus_client` global registry causes `ValueError: Duplicated timeseries` when tests re-import modules.
   - What's unclear: Whether pytest's module isolation is sufficient or if we need `REGISTRY.unregister()` teardown in conftest.
   - Recommendation: Use a `try/except` guard in `custom_metrics.py` to make metric definitions idempotent. Validate in Wave 1 task.

2. **`active_users_gauge` — how to measure "active" users?**
   - What we know: The spec says "active users gauge". The codebase has no concept of an active session beyond JWT tokens.
   - What's unclear: Whether "active" means in-flight requests (`track_inprogress()`) or users with a session in the last N minutes (requires Redis TTL query).
   - Recommendation: Start with `track_inprogress()` — it's trivially accurate and requires zero infrastructure. Document as "in-flight chat requests" rather than "active users." Can be upgraded later.

3. **Grafana dashboard JSON complexity**
   - What we know: A minimal dashboard with 3 panels (request rate, p95 latency, OpenAI latency) can be captured as a ~200-line JSON file.
   - What's unclear: Whether the planner should specify exact panel IDs or leave them to implementation.
   - Recommendation: Planner specifies which metrics/PromQL go in which panel; exact JSON is implementation detail.

---

## Sources

### Primary (HIGH confidence)
- `https://github.com/trallnag/prometheus-fastapi-instrumentator` — version, wiring API, custom metrics closure pattern, lifespan compatibility, pitfalls
- `https://prometheus.io/docs/concepts/metric_types/` — Counter/Gauge/Histogram/Summary definitions
- `https://prometheus.github.io/client_python/exporting/http/fastapi-gunicorn/` — multiprocess mode, `make_asgi_app()` pattern
- `https://prometheus.github.io/client_python/multiprocess/` — PROMETHEUS_MULTIPROC_DIR behavior

### Secondary (MEDIUM confidence)
- `https://last9.io/blog/prometheus-with-docker-compose/` — docker-compose structure; verified against official Prometheus/Grafana docs
- `https://signoz.io/guides/is-prometheus-monitoring-push-or-pull/` — push vs pull explanation; aligns with official Prometheus blog
- `https://medium.com/@dotdc/prometheus-performance-and-cardinality-in-practice-74d5d9cd6230` — cardinality guidance; consistent with official best practices docs

### Tertiary (LOW confidence)
- WebSearch results on middleware ordering and BaseHTTPMiddleware gotchas — consistent across multiple sources but not from an official Prometheus/FastAPI doc

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — library versions confirmed from PyPI and GitHub; docker image tags from official registries
- Architecture patterns: HIGH — wiring patterns verified against official `prometheus-fastapi-instrumentator` README and `prometheus_client` docs
- Pitfalls: MEDIUM-HIGH — duplicated timeseries and cardinality pitfalls confirmed by official docs; middleware ordering from multiple consistent community sources

**Research date:** 2026-03-19
**Valid until:** 2026-06-19 (prometheus-fastapi-instrumentator is stable; Grafana image tag should be re-checked before use)
