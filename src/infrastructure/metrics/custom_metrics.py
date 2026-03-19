"""
Custom Prometheus business metrics for EmotionAI.

Defined at module level so they are registered exactly once in the global
CollectorRegistry. The try/except guards handle the ValueError that occurs
when pytest or uvicorn --reload imports this module a second time.

NEVER define Counter/Gauge/Histogram inside route handlers — that would
attempt re-registration on every request and crash with "Duplicated timeseries".
"""

from prometheus_client import Counter, Gauge, Histogram, REGISTRY

try:
    chat_requests_total = Counter(
        name="emotionai_chat_requests_total",
        documentation="Total chat API requests by agent type and outcome status",
        labelnames=["agent_type", "status"],
        # agent_type: "therapy" | "wellness" (bounded cardinality)
        # status: "success" | "crisis" | "error" (bounded cardinality)
        # DO NOT add user_id — unbounded labels explode Prometheus memory usage.
    )
except ValueError:
    chat_requests_total = REGISTRY._names_to_collectors.get(
        "emotionai_chat_requests_total"
    )

try:
    active_users_gauge = Gauge(
        name="emotionai_active_users_gauge",
        documentation=(
            "Number of chat requests currently in-flight. "
            "Implemented via track_inprogress() — represents concurrent active chat handlers, "
            "not unique users with a session."
        ),
    )
except ValueError:
    active_users_gauge = REGISTRY._names_to_collectors.get(
        "emotionai_active_users_gauge"
    )

try:
    openai_latency_seconds = Histogram(
        name="emotionai_openai_latency_seconds",
        documentation="End-to-end latency of LLM calls (chat completion and semantic tagging)",
        labelnames=["call_type"],
        # call_type: "chat_completion" | "tagging"
        # Buckets cover typical OpenAI response range: fast (100ms) to slow (30s).
        buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    )
except ValueError:
    openai_latency_seconds = REGISTRY._names_to_collectors.get(
        "emotionai_openai_latency_seconds"
    )

# Pre-initialize the bounded label combinations we expect in development/tests
# so /metrics exposes these families before the first chat request lands.
chat_requests_total.labels(agent_type="therapy", status="success")
chat_requests_total.labels(agent_type="therapy", status="crisis")
chat_requests_total.labels(agent_type="therapy", status="error")
openai_latency_seconds.labels(call_type="chat_completion")
openai_latency_seconds.labels(call_type="tagging")
