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

## Further reading

- Official metric types: https://prometheus.io/docs/concepts/metric_types/
- FastAPI instrumentator library: https://github.com/trallnag/prometheus-fastapi-instrumentator
- Python client docs: https://prometheus.github.io/client_python/
- Label cardinality background: https://prometheus.io/docs/practices/naming/
