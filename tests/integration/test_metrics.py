"""
Integration tests for Prometheus metrics endpoint.

Covers requirements M2S1-01 through M2S1-06.

Isolation note: prometheus_client uses a global CollectorRegistry.
custom_metrics.py uses try/except guards so re-importing the module
in the same pytest process does not raise "Duplicated timeseries".
The TestClient uses in-process ASGI transport — no real server port needed.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MockApplicationContainer


@pytest.fixture(scope="module")
def client():
    """Module-scoped client so lifespan fires once and /metrics is registered."""
    mock_container = MockApplicationContainer()

    with (
        patch("main.initialize_container", new=AsyncMock(return_value=mock_container)),
        patch("main.shutdown_container", new=AsyncMock()),
    ):
        from main import create_application
        from src.presentation.api.routers.deps import get_container

        app = create_application()
        app.dependency_overrides[get_container] = lambda: mock_container

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

        app.dependency_overrides.clear()


def test_metrics_endpoint_returns_200(client):
    """M2S1-01: GET /metrics returns HTTP 200."""
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_content_type_is_text_plain(client):
    """M2S1-01: Content-Type must be text/plain."""
    response = client.get("/metrics")
    assert "text/plain" in response.headers["content-type"]


def test_metrics_contain_http_requests_total_after_request(client):
    """M2S1-02: auto-instrumented counter appears after at least one routed request."""
    client.get("/health/")
    response = client.get("/metrics")
    assert "http_requests_total" in response.text


def test_chat_counter_present_in_metrics(client):
    """M2S1-03: emotionai_chat_requests_total is registered and appears in /metrics."""
    response = client.get("/metrics")
    assert "emotionai_chat_requests_total" in response.text


def test_openai_histogram_buckets_present(client):
    """M2S1-04: emotionai_openai_latency_seconds histogram buckets appear in output."""
    response = client.get("/metrics")
    assert "emotionai_openai_latency_seconds_bucket" in response.text


def test_active_users_gauge_present(client):
    """M2S1-05: emotionai_active_users_gauge is registered and appears in /metrics."""
    response = client.get("/metrics")
    assert "emotionai_active_users_gauge" in response.text


def test_metrics_not_rate_limited(client):
    """M2S1-06: /metrics must return 200 even after many prior requests."""
    for _ in range(70):
        client.get("/health/")

    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.status_code != 429


def test_metrics_prometheus_help_lines_present(client):
    """Sanity check: # HELP lines exist for all three custom metrics."""
    response = client.get("/metrics")
    body = response.text
    assert "# HELP emotionai_chat_requests_total" in body
    assert "# HELP emotionai_active_users_gauge" in body
    assert "# HELP emotionai_openai_latency_seconds" in body


def test_metrics_custom_histogram_buckets(client):
    """OpenAI histogram uses custom buckets up to 30s."""
    response = client.get("/metrics")
    assert 'le="30.0"' in response.text
