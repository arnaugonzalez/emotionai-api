"""Tests for src/infrastructure/telemetry/tracing.py — covers OTEL-01 and OTEL-02."""

import pytest
from unittest.mock import patch, MagicMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from src.infrastructure.telemetry.tracing import setup_tracing, get_tracer


@pytest.fixture(autouse=True)
def reset_tracer_provider():
    """Reset global TracerProvider between tests to avoid state leakage."""
    original = trace.get_tracer_provider()
    yield
    trace.set_tracer_provider(original)


def test_setup_tracing_enabled_registers_provider():
    """OTEL-01: TracerProvider is registered when enabled=True."""
    with patch("src.infrastructure.telemetry.tracing.OTLPSpanExporter") as mock_exp, \
         patch("src.infrastructure.telemetry.tracing.AsyncPGInstrumentor") as mock_asyncpg, \
         patch("src.infrastructure.telemetry.tracing.HTTPXClientInstrumentor") as mock_httpx:
        mock_exp.return_value = MagicMock()
        mock_asyncpg.return_value.instrument = MagicMock()
        mock_httpx.return_value.instrument = MagicMock()

        setup_tracing(
            service_name="test-service",
            service_version="0.0.1",
            environment="testing",
            otlp_endpoint="http://localhost:4318",
            enabled=True,
        )

    provider = trace.get_tracer_provider()
    assert isinstance(provider, TracerProvider), "Expected a real TracerProvider, got no-op"


def test_setup_tracing_disabled_is_noop():
    """OTEL-02: setup_tracing(enabled=False) leaves the default provider unchanged."""
    before = trace.get_tracer_provider()

    setup_tracing(
        service_name="test-service",
        service_version="0.0.1",
        environment="testing",
        otlp_endpoint="http://localhost:4318",
        enabled=False,
    )

    after = trace.get_tracer_provider()
    assert before is after, "setup_tracing(enabled=False) must not change the TracerProvider"


def test_setup_tracing_appends_v1_traces_to_endpoint():
    """OTEL critical: exporter endpoint must end with /v1/traces."""
    captured_endpoint = {}

    def capture_exporter(*args, **kwargs):
        captured_endpoint["endpoint"] = kwargs.get("endpoint", args[0] if args else None)
        return MagicMock()

    with patch("src.infrastructure.telemetry.tracing.OTLPSpanExporter", side_effect=capture_exporter), \
         patch("src.infrastructure.telemetry.tracing.AsyncPGInstrumentor") as mock_asyncpg, \
         patch("src.infrastructure.telemetry.tracing.HTTPXClientInstrumentor") as mock_httpx:
        mock_asyncpg.return_value.instrument = MagicMock()
        mock_httpx.return_value.instrument = MagicMock()

        setup_tracing(
            service_name="s",
            service_version="1",
            environment="testing",
            otlp_endpoint="http://jaeger:4318",
            enabled=True,
        )

    assert captured_endpoint["endpoint"] == "http://jaeger:4318/v1/traces"


def test_get_tracer_returns_tracer():
    """get_tracer() returns a usable Tracer object."""
    tracer = get_tracer("test.module")
    assert tracer is not None
    # Should support context manager span creation
    with tracer.start_as_current_span("test-span") as span:
        assert span is not None
