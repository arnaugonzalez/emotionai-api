"""Unit tests for LangChainAgentService OTEL spans — covers OTEL-03.

Uses InMemorySpanExporter so Jaeger is not required.

Design note: The service holds _tracer = get_tracer(__name__) at class definition time.
The OTEL SDK prevents overriding an already-set TracerProvider, so we inject a fresh
tracer from the test provider directly onto the service instance for each test.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from src.infrastructure.services.langchain_agent_service import LangChainAgentService
from src.domain.chat.entities import TherapyResponse
from datetime import datetime, timezone


@pytest.fixture
def span_exporter():
    """Return an (exporter, provider) pair for span capture.

    Rather than swapping the global TracerProvider (which the OTEL SDK restricts after
    first use), we inject the test provider's tracer directly onto the service instance.
    """
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    yield exporter, provider
    exporter.clear()


def _make_therapy_response(crisis_detected: bool = False) -> TherapyResponse:
    return TherapyResponse(
        message="I hear you. That sounds really difficult.",
        agent_type="therapy",
        conversation_id="conv-123",
        timestamp=datetime.now(timezone.utc),
        therapeutic_approach="cognitive_behavioral",
        emotional_tone="empathetic",
        follow_up_suggestions=["Try journaling your thoughts"],
        crisis_detected=crisis_detected,
        metadata={},
    )


def _make_service(provider: TracerProvider) -> LangChainAgentService:
    """Build a LangChainAgentService with all dependencies mocked and the tracer
    injected from the test provider so spans land in the test exporter."""
    llm_service = MagicMock()
    llm_service.generate_therapy_response = AsyncMock(return_value=_make_therapy_response())
    llm_service.analyze_emotional_state = AsyncMock(return_value={"emotion": "anxious", "crisis_indicators": []})
    llm_service.health_check = AsyncMock(return_value=True)

    conv_repo = MagicMock()
    conv_repo.get_conversation_history = AsyncMock(return_value=[])
    conv_repo.save_conversation = AsyncMock(return_value="conv-123")
    conv_repo.add_message = AsyncMock(return_value=MagicMock())
    conv_repo.get_recent_context = AsyncMock(return_value=[])

    user_repo = MagicMock()
    user_repo.get_by_id = AsyncMock(return_value=None)

    record_repo = MagicMock()
    record_repo.get_records_by_date_range = AsyncMock(return_value=[])

    service = LangChainAgentService(
        llm_service=llm_service,
        conversation_repository=conv_repo,
        user_repository=user_repo,
        emotional_repository=record_repo,
        settings={"openai_model": "gpt-4"},
    )
    # Inject test-local tracer so spans go to our InMemorySpanExporter
    service._tracer = provider.get_tracer(__name__)
    return service


@pytest.mark.asyncio
async def test_llm_generate_creates_span(span_exporter):
    """OTEL-03: send_message emits a span named emotionai.chat.llm_generate."""
    exporter, provider = span_exporter
    service = _make_service(provider)
    user_id = uuid4()

    await service.send_message(user_id, "therapy", "I feel anxious today", {})

    spans = exporter.get_finished_spans()
    span_names = [s.name for s in spans]
    assert "emotionai.chat.llm_generate" in span_names, (
        f"Expected 'emotionai.chat.llm_generate' in spans, got: {span_names}"
    )


@pytest.mark.asyncio
async def test_llm_generate_span_has_user_id_attribute(span_exporter):
    """OTEL-03: emotionai.chat.llm_generate span carries the user.id attribute."""
    exporter, provider = span_exporter
    service = _make_service(provider)
    user_id = uuid4()

    await service.send_message(user_id, "therapy", "I feel anxious today", {})

    spans = exporter.get_finished_spans()
    llm_span = next(s for s in spans if s.name == "emotionai.chat.llm_generate")
    assert "user.id" in llm_span.attributes, "user.id attribute missing from span"
    assert llm_span.attributes["user.id"] == str(user_id)


@pytest.mark.asyncio
async def test_llm_generate_span_has_model_attribute(span_exporter):
    """OTEL-03: emotionai.chat.llm_generate span carries the llm.model attribute."""
    exporter, provider = span_exporter
    service = _make_service(provider)

    await service.send_message(uuid4(), "therapy", "Hello", {})

    spans = exporter.get_finished_spans()
    llm_span = next(s for s in spans if s.name == "emotionai.chat.llm_generate")
    assert "llm.model" in llm_span.attributes
    assert llm_span.attributes["llm.model"] == "gpt-4"


@pytest.mark.asyncio
async def test_llm_generate_span_completed_on_success(span_exporter):
    """OTEL-03: span is finished (not still-open) after a successful call."""
    exporter, provider = span_exporter
    service = _make_service(provider)

    await service.send_message(uuid4(), "therapy", "Tell me more", {})

    spans = exporter.get_finished_spans()
    llm_span = next(s for s in spans if s.name == "emotionai.chat.llm_generate")
    # A finished span has end_time set
    assert llm_span.end_time is not None, "Span was not finished after successful call"


@pytest.mark.asyncio
async def test_llm_generate_span_has_agent_type_attribute(span_exporter):
    """OTEL-03: span records the agent_type so traces are filterable by agent."""
    exporter, provider = span_exporter
    service = _make_service(provider)

    await service.send_message(uuid4(), "wellness", "I need help", {})

    spans = exporter.get_finished_spans()
    llm_span = next(s for s in spans if s.name == "emotionai.chat.llm_generate")
    assert llm_span.attributes.get("chat.agent_type") == "wellness"


@pytest.mark.asyncio
async def test_llm_generate_span_crisis_attribute_set_when_detected(span_exporter):
    """OTEL-03: crisis_detected attribute is set on span when therapy response signals crisis."""
    exporter, provider = span_exporter
    service = _make_service(provider)
    # Override the LLM mock to return a crisis response
    service.llm_service.generate_therapy_response = AsyncMock(
        return_value=_make_therapy_response(crisis_detected=True)
    )

    await service.send_message(uuid4(), "therapy", "I can't go on", {})

    spans = exporter.get_finished_spans()
    llm_span = next(s for s in spans if s.name == "emotionai.chat.llm_generate")
    assert llm_span.attributes.get("crisis_detected") is True
