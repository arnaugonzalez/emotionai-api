"""
TracerProvider factory for EmotionAI.

Initialize once at app startup (inside FastAPI lifespan), not at module level.
Module-level init breaks uvicorn --reload (child processes don't cleanly inherit OTEL state).
"""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor


def setup_tracing(
    service_name: str,
    service_version: str,
    environment: str,
    otlp_endpoint: str,
    enabled: bool = True,
) -> None:
    """Initialize the global TracerProvider with OTLP HTTP export to Jaeger.

    Args:
        service_name: Value for the service.name resource attribute.
        service_version: Value for the service.version resource attribute.
        environment: deployment.environment attribute (development / production).
        otlp_endpoint: Base URL of the OTLP HTTP receiver, e.g. "http://jaeger:4318".
                       The /v1/traces path is appended internally.
        enabled: If False, this function is a no-op (useful for testing environments
                 that don't have Jaeger running).
    """
    if not enabled:
        return

    resource = Resource.create(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": environment,
    })

    exporter = OTLPSpanExporter(
        endpoint=f"{otlp_endpoint}/v1/traces",
    )

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # Instrument asyncpg BEFORE any asyncpg connections are created.
    # ApplicationContainer creates the engine in initialize_container(), which runs
    # after setup_tracing() in the lifespan — so this ordering is safe.
    AsyncPGInstrumentor().instrument()

    # Instrument all httpx clients — catches outbound OpenAI SDK calls.
    # Note: if OpenAI SDK creates its httpx client at import time (before this call),
    # those clients won't be instrumented. Verify during smoke test that
    # "POST https://api.openai.com/v1/chat/completions" spans appear as children
    # of emotionai.chat.llm_generate. If not, add a manual span in OpenAITaggingService.
    HTTPXClientInstrumentor().instrument()


def get_tracer(name: str) -> trace.Tracer:
    """Return a tracer for the given instrumentation scope.

    Args:
        name: Typically __name__ of the calling module.
    Returns:
        A Tracer from the globally registered TracerProvider.
        If setup_tracing() has not been called, returns a no-op Tracer.
    """
    return trace.get_tracer(name)
