# Prometheus + FastAPI — EmotionAI study guide

## What is it and why do we use it here

EmotionAI already has logs through middleware such as `LoggingMiddleware`. Logs answer
"what happened?" for a single request. Metrics answer "how much?", "how often?", and
"how fast?" across many requests.

In this slice, metrics give us direct visibility into backend behavior:

- `emotionai_active_users_gauge`: how many chat requests are in flight right now
- `emotionai_chat_requests_total`: how many chat requests succeeded, failed, or hit a crisis path
- `emotionai_openai_latency_seconds`: how long the AI-facing work takes

That matters in a mental-health app because operational questions are product questions:

- Are users currently chatting right now?
- Is OpenAI latency drifting up and making the app feel slow?
- Are crisis-tagged conversations rare or spiking?

This is one pillar of observability:

- Logs: detailed event records
- Metrics: aggregated numeric signals
- Traces: request flow across components

EmotionAI now has logs and metrics. Tracing is planned for Milestone 2, Slice 2.3.

## How it works conceptually (explain as if to a junior developer)

Prometheus uses a pull model, not a push model.

Push model:

- The application sends metrics to a central service
- Example family: StatsD-style setups
- Good for fire-and-forget emission
- Weakness: if the app dies silently, it stops pushing and the central server has less context about that failure

Pull model:

- The application exposes metrics at an HTTP endpoint, usually `/metrics`
- Prometheus calls that endpoint on a schedule and scrapes the latest values
- If the app does not respond, Prometheus marks the target `DOWN`
- The app does not need to know where Prometheus lives

That is exactly what EmotionAI does now. The API exposes `/metrics`, and Prometheus scrapes it.

Real EmotionAI scrape config:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "emotionai-api"
    scrape_interval: 10s
    metrics_path: "/metrics"
    static_configs:
      - targets: ["api:8000"]
        labels:
          environment: "development"
```

Why `api:8000` and not `localhost:8000`?

- Inside `docker-compose`, containers talk to each other by service name
- The API, Prometheus, and Grafana all join `emotionai-network`
- From the Prometheus container's point of view, the API is reachable at `api:8000`

This is one of the main reasons Prometheus is popular: the app stays simple. It just exposes state.

When does push make more sense?

- Short-lived batch jobs
- One-off CLI jobs
- Tasks that finish before Prometheus has time to scrape them

In those cases, Prometheus usually works with Pushgateway rather than direct scraping.

## Key patterns used in this project (with code examples from the actual codebase)

### 1. Auto-instrument FastAPI after middleware registration

EmotionAI wires the instrumentator in [`main.py`](/home/eager-eagle/code/emotionai/emotionai-api/main.py) after all `app.add_middleware(...)` calls:

```python
instrumentator = (
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=[r"/metrics", r"/health.*"],
    )
    .instrument(app)
)
app.state.instrumentator = instrumentator
```

Why here?

- FastAPI middleware wraps the ASGI app layer-by-layer
- If instrumentation runs before middleware registration, those middleware layers are not part of what gets measured
- Excluding `/metrics` avoids the scrape endpoint measuring itself
- Excluding `/health.*` keeps probes from polluting request metrics

EmotionAI exposes the route during lifespan startup, also in [`main.py`](/home/eager-eagle/code/emotionai/emotionai-api/main.py):

```python
container = await initialize_container(settings.__dict__)
app.state.container = container
app.state.instrumentator.expose(app, include_in_schema=False)
```

Why expose in lifespan instead of module import time?

- The app is fully configured at that point
- Middleware and app state are already in place
- It fits EmotionAI's existing startup model cleanly

### 2. Counter: completed events only ever go up

EmotionAI defines its custom metrics in [`custom_metrics.py`](/home/eager-eagle/code/emotionai/emotionai-api/src/infrastructure/metrics/custom_metrics.py):

```python
chat_requests_total = Counter(
    name="emotionai_chat_requests_total",
    documentation="Total chat API requests by agent type and outcome status",
    labelnames=["agent_type", "status"],
)
```

Counters only increase. They reset to zero on process restart because they live in process memory.

The chat router increments that counter in [`chat.py`](/home/eager-eagle/code/emotionai/emotionai-api/src/presentation/api/routers/chat.py):

```python
chat_requests_total.labels(
    agent_type=payload.agent_type or "therapy",
    status=status_label,
).inc()
```

EmotionAI uses bounded labels:

- `agent_type`: expected low-cardinality values such as `therapy`
- `status`: `success`, `crisis`, `error`

Typical PromQL with a counter:

```promql
rate(emotionai_chat_requests_total[5m])
```

That turns a raw ever-increasing counter into requests-per-second over a rolling time window.

### 3. Gauge: current state can move up and down

EmotionAI tracks active chat handlers with a gauge:

```python
active_users_gauge = Gauge(
    name="emotionai_active_users_gauge",
    documentation="Number of chat requests currently in-flight...",
)
```

Then it wraps the handler with `track_inprogress()` in [`chat.py`](/home/eager-eagle/code/emotionai/emotionai-api/src/presentation/api/routers/chat.py):

```python
with active_users_gauge.track_inprogress():
    response = await chat_use_case.execute(...)
```

This increments when the request enters the block and decrements when it leaves, even if an exception happens.

Why call it "active users" if it is really in-flight requests?

- EmotionAI does not have a separate session-presence system
- The most honest operational definition available right now is concurrent active chat work
- That makes the metric useful without inventing fake session logic

### 4. Histogram: bucket observations for latency analysis

EmotionAI tracks LLM latency with a histogram:

```python
openai_latency_seconds = Histogram(
    name="emotionai_openai_latency_seconds",
    documentation="End-to-end latency of LLM calls...",
    labelnames=["call_type"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)
```

The router records an observation like this:

```python
openai_latency_seconds.labels(call_type="chat_completion").observe(
    time.perf_counter() - start
)
```

Why custom buckets?

- The default histogram buckets top out around 10 seconds
- OpenAI-backed work can easily take 15-30 seconds in slow cases
- Without a 30-second bucket, slow calls collapse into `+Inf`, which makes percentiles less useful

Example percentile query:

```promql
histogram_quantile(
  0.95,
  sum(rate(emotionai_openai_latency_seconds_bucket[5m])) by (call_type, le)
)
```

### 5. `/metrics` output format

Prometheus expects plaintext exposition format. A real slice of EmotionAI output looks like this:

```text
# HELP emotionai_chat_requests_total Total chat API requests by agent type and outcome status
# TYPE emotionai_chat_requests_total counter
emotionai_chat_requests_total{agent_type="therapy",status="success"} 0.0
# HELP emotionai_openai_latency_seconds End-to-end latency of LLM calls (chat completion and semantic tagging)
# TYPE emotionai_openai_latency_seconds histogram
emotionai_openai_latency_seconds_bucket{call_type="chat_completion",le="0.1"} 0.0
emotionai_openai_latency_seconds_bucket{call_type="chat_completion",le="30.0"} 0.0
emotionai_openai_latency_seconds_count{call_type="chat_completion"} 0.0
emotionai_openai_latency_seconds_sum{call_type="chat_completion"} 0.0
```

How to read that:

- `# HELP`: human description
- `# TYPE`: metric family type
- Plain metric line: current sample value
- `_bucket`: histogram bucket counts
- `_count`: number of observations
- `_sum`: total observed value across all samples

EmotionAI also exposes auto-instrumented HTTP metrics such as `http_requests_total`.

### 6. Local observability stack

Prometheus is configured in [`prometheus/prometheus.yml`](/home/eager-eagle/code/emotionai/emotionai-api/prometheus/prometheus.yml) and Grafana is auto-provisioned through:

- [`grafana/provisioning/datasources/prometheus.yml`](/home/eager-eagle/code/emotionai/emotionai-api/grafana/provisioning/datasources/prometheus.yml)
- [`grafana/provisioning/dashboards/dashboards.yml`](/home/eager-eagle/code/emotionai/emotionai-api/grafana/provisioning/dashboards/dashboards.yml)
- [`grafana/provisioning/dashboards/emotionai.json`](/home/eager-eagle/code/emotionai/emotionai-api/grafana/provisioning/dashboards/emotionai.json)

That means:

- Prometheus starts with the correct scrape target
- Grafana starts already connected to Prometheus
- No manual UI setup is required to begin inspecting the metrics

## Common mistakes and how to avoid them

### 1. Defining metrics inside route handlers

Bad:

```python
@router.post("/chat")
async def chat_with_agent(...):
    counter = Counter("emotionai_chat_requests_total", "...")
    counter.inc()
```

Why this fails:

- Every request tries to register the metric again
- `prometheus_client` raises `ValueError: Duplicated timeseries`

Good:

```python
# src/infrastructure/metrics/custom_metrics.py
chat_requests_total = Counter(...)
```

Then import and use that shared module-level metric.

### 2. High-cardinality labels

Bad idea:

```python
chat_requests_total.labels(
    user_id=str(current_user_id),
    agent_type="therapy",
    status="success",
).inc()
```

Why this is dangerous:

- 1000 users × 2 agent types × 3 statuses = 6000 time series
- Prometheus stores all label combinations in memory
- That grows fast and can lead to memory pressure or OOM

EmotionAI avoids this by keeping labels bounded and low-cardinality.

### 3. Instrumenting before middleware is added

Bad order:

```python
app = FastAPI(...)
Instrumentator().instrument(app)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitingMiddleware)
```

Why this is wrong:

- The middleware stack was not fully wrapped when instrumentation attached
- Your metrics no longer describe the full real request path

EmotionAI uses the correct order in [`main.py`](/home/eager-eagle/code/emotionai/emotionai-api/main.py): middleware first, instrumentation second.

### 4. Forgetting multi-process setup in production

EmotionAI's local docker-compose dev setup runs a single API process, so the default in-memory registry is fine.

Production is different if uvicorn runs multiple workers:

- Each worker gets its own process memory
- Each worker keeps its own Prometheus registry
- A single scrape cannot see all workers unless multiprocess mode is configured

Typical fix:

```bash
export PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus_multiproc
```

Then configure the Python client for multiprocess collection.

This is not required for the current development stack, but it becomes mandatory if EmotionAI keeps `workers=4` in production and wants accurate aggregated metrics.

## Hardened demo runner usage

The observability slice now includes a modular bash runner at [`scripts/demo_flow.sh`](/home/eager-eagle/code/emotionai/emotionai-api/scripts/demo_flow.sh) that is meant for demos, learning, and quick smoke checks.

Useful commands:

```bash
bash scripts/demo_flow.sh --list-steps
bash scripts/demo_flow.sh --section metrics --base-url http://127.0.0.1:8000
bash scripts/demo_flow.sh --section all --base-url http://127.0.0.1:8000
```

What the sections mean:

- `metrics`: required checks for `/metrics` availability, Prometheus text format, and EmotionAI metric families
- `celery`: optional future checks for Flower/Celery prerequisites and reachability
- `otel`: optional future checks for Jaeger and OTLP readiness
- `all`: runs every registered step and exits non-zero only if a required step fails

Failure troubleshooting flow:

1. Read the step result line for the exact failed condition.
2. Use the `remediation=` hint printed under that step.
3. Open the run artifact directory printed as `artifacts=...`.
4. Inspect the per-step files such as `.body`, `.stderr`, `.headers`, and `step.log`.

Artifact layout example:

```text
.tmp/demo_flow/20260319T133625Z/
  metrics.endpoint/
    http.body
    http.stderr
    http.headers
    reason.txt
    remediation.txt
    step.log
```

This matters because demo failures are no longer "something is wrong". They now tell you whether the problem is transport (`curl` could not connect), HTTP contract (`status != 200`), or exposition content (missing metric families or headers).

## Further reading

- Official metric types: https://prometheus.io/docs/concepts/metric_types/
- FastAPI instrumentator library: https://github.com/trallnag/prometheus-fastapi-instrumentator
- Python client docs: https://prometheus.github.io/client_python/
- Label cardinality background: https://prometheus.io/docs/practices/naming/

## When to use Prometheus (vs alternatives)

| Scenario | Best tool | Why |
|----------|-----------|-----|
| Long-running service exposing current state | Prometheus pull | Target availability is itself a data point. Down = `UP == 0`, alert fires automatically. |
| Short-lived batch job or CLI script | Pushgateway + Prometheus | Job finishes before scrape interval; push at job end instead. |
| Sub-second resolution required | StatsD + Graphite | Prometheus scrape granularity is 10-15s by design. |
| Per-request timeline ("why was *this* request slow?") | OpenTelemetry traces | Metrics are aggregate signals; traces are per-request waterfall views. |
| Spike investigation ("*which* function caused it?") | Structured logs or OTel spans | Prometheus tells you the rate spiked; logs/traces name the culprit. |
| Real-time alerting on error rates | Prometheus + Alertmanager | `rate()` over short windows is ideal for alert rule expressions. |
| Multi-process uvicorn in production | Prometheus multiprocess mode | Single-process in-memory registry cannot see other workers without it. |

EmotionAI decision: Prometheus for aggregate latency and request counts; OpenTelemetry for per-request
span-level breakdown. These are complementary, not competing.

## Advanced code examples

### Summary vs Histogram — when to use which

```python
from prometheus_client import Summary

# Summary computes quantiles client-side per process.
# Correct for single-process deployments, but quantiles cannot be
# mathematically aggregated across multiple workers.
openai_latency_summary = Summary(
    "emotionai_openai_latency_summary_seconds",
    "LLM call latency (client-side quantiles)",
    labelnames=["call_type"],
)

with openai_latency_summary.labels(call_type="chat_completion").time():
    result = await chat_use_case.execute(...)
```

Why EmotionAI uses Histogram instead of Summary:

- `sum(rate(emotionai_openai_latency_seconds_bucket[5m]))` aggregates correctly across N workers.
- Summary quantiles per worker cannot be combined — `quantile(0.95)` across 4 workers is not the
  real p95 of all requests.
- EmotionAI will scale horizontally; Histogram is the correct choice.

### Reading a metric value in tests

```python
from src.infrastructure.metrics.custom_metrics import chat_requests_total

def test_counter_increments_on_success():
    before = chat_requests_total.labels(
        agent_type="therapy", status="success"
    )._value.get()
    # trigger a chat request via TestClient ...
    after = chat_requests_total.labels(
        agent_type="therapy", status="success"
    )._value.get()
    assert after == before + 1
```

`_value` is a prometheus_client internal. Using it in tests is acceptable; avoid it in production code.

### Programmatic metrics endpoint assertion (Python equivalent of demo_steps/10_metrics.sh)

```python
import httpx

async def assert_metrics_healthy(base_url: str) -> None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{base_url}/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    for family in [
        "emotionai_chat_requests_total",
        "emotionai_openai_latency_seconds_bucket",
        "emotionai_active_users_gauge",
    ]:
        assert family in resp.text, f"Missing metric family: {family}"
```

### Alertmanager rule for crisis detection

```yaml
# prometheus_rules.yml
groups:
  - name: emotionai
    rules:
      - alert: CrisisRateSpike
        expr: rate(emotionai_chat_requests_total{status="crisis"}[5m]) > 0.1
        for: 2m
        labels:
          severity: page
        annotations:
          summary: "Crisis conversations spiking (>0.1/s sustained 2m)"
```

## Interview Prep — Prometheus

**Q1: What is the difference between a Counter, Gauge, and Histogram? Give a real example of each.**

Counter: only increases, resets on restart. Use for cumulative events. Example in EmotionAI:
`emotionai_chat_requests_total` counts every completed chat request by agent_type and status.
Gauge: current snapshot, can go up or down. Example: `emotionai_active_users_gauge` reflects how
many chat handlers are in flight right now. Histogram: buckets observations for percentile queries.
Example: `emotionai_openai_latency_seconds` with custom buckets up to 30s captures the full range
of LLM response times.

**Q2: Why does EmotionAI use custom histogram buckets instead of the defaults?**

The default prometheus_client buckets top out around 10 seconds. OpenAI-backed work can take
15-30 seconds under load. Without a 30-second bucket, slow calls collapse into `+Inf`. The
`histogram_quantile` function cannot estimate percentiles beyond the largest explicit bucket, so
p95 and p99 become meaningless for tail latency. Custom buckets: `(0.1, 0.25, 0.5, 1.0, 2.5,
5.0, 10.0, 30.0)`.

**Q3: Why is high-cardinality labeling dangerous?**

Every unique label combination is a separate time series stored in Prometheus memory. 10,000
users × 3 statuses × 2 agent types = 60,000 series. Prometheus is designed for thousands of
series, not millions. Memory climbs, scrapes time out, queries slow. EmotionAI keeps labels
bounded: `status` has 3 values, `agent_type` stays at low cardinality.

**Q4: What is the difference between `rate()` and `irate()`?**

`rate()` uses all samples in the window and smooths them — good for dashboards and trend views.
`irate()` uses only the last two samples — more reactive but noisier, suited for alerting where
you want to catch recent sharp changes. Use `rate()` in Grafana panels, `irate()` in alert rules
where reaction speed matters.

**Q5: Why does EmotionAI expose `/metrics` in lifespan startup rather than at module import time?**

FastAPI middleware is added layer by layer during app configuration. If instrumentation runs before
middleware registration, the ASGI stack it wraps is incomplete. Latency measurements would not
include time spent inside LoggingMiddleware or RateLimitingMiddleware. Lifespan startup guarantees
the full middleware stack exists before the instrumentator attaches.

**Q6: How does `prometheus_fastapi_instrumentator` work internally?**

It installs an ASGI middleware that intercepts every response after it is generated. It extracts
templated path (e.g. `/users/{id}` not `/users/123`), HTTP method, status code group, and
response time, then records them into histogram buckets using the standard prometheus_client
library. `should_ignore_untemplated=True` drops requests that did not match any route, preventing
one-off paths (e.g. `/favicon.ico`) from spawning unique time series.

**Q7: What happens to counters when the process restarts?**

They reset to zero because they live in process memory. PromQL `rate()` handles this via counter
reset detection: if a scraped value is lower than the previous scrape, Prometheus assumes a restart
and treats the new lower value as the new baseline. No spike appears in `rate()` output.

**Q8: How would you set up Prometheus for a uvicorn deployment with 4 workers?**

Set `PROMETHEUS_MULTIPROC_DIR` to a writable shared directory. Configure prometheus_client to use
`MultiProcessCollector`. Each worker writes metrics to separate files in that directory.
When Prometheus scrapes `/metrics`, one collector aggregates all worker files and returns merged
results. Without this, each worker has its own in-memory registry; a scrape only sees one worker's
data nondeterministically.

**Q9: What does the `should_group_status_codes=True` flag do in Instrumentator?**

It groups status codes into families: 2xx, 3xx, 4xx, 5xx rather than keeping 200, 201, 204, 400,
404, etc. as separate label values. This controls cardinality: without grouping, each distinct
status code is a separate label value per route, multiplying time series.

**Q10: What is Pushgateway and when would EmotionAI need it?**

Pushgateway is an intermediary that accepts pushed metrics from short-lived jobs and holds them
for Prometheus to scrape. EmotionAI would need it for things like a nightly database cleanup
script, a one-off migration runner, or any job that starts and finishes in under 15 seconds —
before Prometheus would have time to scrape the job's `/metrics` endpoint directly.

## Gotchas interviewers test on

**"Can you register the same metric name twice in the same process?"**
No. prometheus_client raises `ValueError: Duplicated timeseries in CollectorRegistry`. This is
why EmotionAI defines all custom metrics once in `src/infrastructure/metrics/custom_metrics.py`
and imports the shared instances. Defining metrics inside route handlers or calling the
constructor on every request triggers this error on the second request.

**"What does `le` stand for in histogram output?"**
"Less than or equal." `emotionai_openai_latency_seconds_bucket{le="1.0"}` contains the count of
observations where latency was ≤ 1.0 second. The `+Inf` bucket always equals `_count` because
every observation is ≤ infinity. Common wrong answer: "label equals."

**"Is `histogram_quantile` exact?"**
No. It assumes uniform distribution within each bucket. Accuracy depends on how tightly the
buckets bracket the percentile of interest. EmotionAI's 0.5-1.0 bucket is the key range for p50;
tighter buckets there would give a more accurate p50 estimate.

**"If a spike lasts 10 seconds and your scrape interval is 15 seconds, will Prometheus detect it?"**
Likely not. Prometheus captures point-in-time samples; events between scrapes are invisible. For
sub-scrape-interval visibility, you need a shorter scrape interval (more load), counters (the
spike increments are cumulative and will appear on next scrape as a large `rate()`), or event-based
logging/tracing.

**"What is the instrumentation order bug?"**
Calling `Instrumentator().instrument(app)` before `app.add_middleware(...)` means the middleware
layers are not inside the measured ASGI path. Timing observations skip the real overhead. The fix
is always: add all middleware first, then instrument.

**"Why does `track_inprogress()` still decrement even on exception?"**
Because it is a context manager using `__exit__`. Python guarantees `__exit__` runs even if an
exception propagates through the `with` block. EmotionAI uses this on `active_users_gauge` in
`chat.py` so a crashed chat handler does not permanently inflate the in-flight count.
