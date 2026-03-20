"""Unit tests for OpenAITaggingService OTEL spans — covers OTEL-04.

Uses InMemorySpanExporter so Jaeger is not required.

Design note: The service holds _tracer = get_tracer(__name__) at class definition time.
The OTEL SDK prevents overriding an already-set TracerProvider, so we inject a fresh
tracer from the test provider directly onto the service instance for each test.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from src.infrastructure.services.openai_tagging_service import OpenAITaggingService


@pytest.fixture
def span_exporter():
    """Return an (exporter, provider) pair for span capture."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield exporter, provider
    exporter.clear()


def _fake_openai_response(tags: list = None) -> MagicMock:
    """Build a minimal fake openai ChatCompletion response."""
    tags = tags or ["anxious", "seeking_help"]
    payload = {
        "tags": tags,
        "confidence": 0.85,
        "categories": {"emotional": tags},
        "insights": ["User is seeking support"],
    }
    choice = MagicMock()
    choice.message.content = json.dumps(payload)
    response = MagicMock()
    response.choices = [choice]
    response.usage = None
    return response


def _make_service(provider: TracerProvider) -> OpenAITaggingService:
    """Build an OpenAITaggingService with a mocked OpenAI client and injected test tracer."""
    service = OpenAITaggingService(api_key="test-key", model="gpt-4o-mini")
    service.client = MagicMock()
    service.client.chat.completions.create = AsyncMock(return_value=_fake_openai_response())
    # Inject test-local tracer so spans go to our InMemorySpanExporter
    service._tracer = provider.get_tracer(__name__)
    return service


@pytest.mark.asyncio
async def test_classify_creates_span(span_exporter):
    """OTEL-04: extract_tags_from_message emits a span named emotionai.tagging.classify."""
    exporter, provider = span_exporter
    service = _make_service(provider)

    await service.extract_tags_from_message("I am feeling very anxious today")

    spans = exporter.get_finished_spans()
    span_names = [s.name for s in spans]
    assert "emotionai.tagging.classify" in span_names, (
        f"Expected 'emotionai.tagging.classify' in spans, got: {span_names}"
    )


@pytest.mark.asyncio
async def test_classify_span_has_input_length_attribute(span_exporter):
    """OTEL-04: span carries input.length so we can track prompt sizes."""
    exporter, provider = span_exporter
    service = _make_service(provider)
    content = "I am feeling very anxious today"

    await service.extract_tags_from_message(content)

    spans = exporter.get_finished_spans()
    span = next(s for s in spans if s.name == "emotionai.tagging.classify")
    assert span.attributes.get("input.length") == len(content)


@pytest.mark.asyncio
async def test_classify_span_has_model_attribute(span_exporter):
    """OTEL-04: span records which model was used for the tagging call."""
    exporter, provider = span_exporter
    service = _make_service(provider)

    await service.extract_tags_from_message("Need help")

    spans = exporter.get_finished_spans()
    span = next(s for s in spans if s.name == "emotionai.tagging.classify")
    assert span.attributes.get("llm.model") == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_classify_span_completed_after_call(span_exporter):
    """OTEL-04: span is finished after a successful tagging call."""
    exporter, provider = span_exporter
    service = _make_service(provider)

    await service.extract_tags_from_message("Feeling low today")

    spans = exporter.get_finished_spans()
    span = next(s for s in spans if s.name == "emotionai.tagging.classify")
    assert span.end_time is not None, "Span was not finished after successful call"
