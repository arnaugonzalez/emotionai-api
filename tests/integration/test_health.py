"""
Integration tests for the /health endpoint.

These tests use FastAPI's TestClient (httpx-backed) with a mocked
ApplicationContainer injected via dependency_overrides. No real database,
Redis, or OpenAI calls are made.

Endpoints covered:
  GET /health        — basic health check, no auth required
  GET /health/live   — liveness probe, no auth required
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from tests.conftest import MockApplicationContainer


# ---------------------------------------------------------------------------
# Shared fixture: TestClient with mocked container
#
# Strategy: import the module-level `app` from main.py and override the
# `get_container` dependency so that routers never see the real container.
# We also patch `initialize_container` and `shutdown_container` in the lifespan
# so TestClient startup does not attempt real DB/Redis/OpenAI connections.
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    TestClient with mocked ApplicationContainer.

    The real lifespan normally calls initialize_container() which connects to
    PostgreSQL + Redis. We patch both lifecycle functions so the test process
    never touches real infrastructure.

    The mocked container is injected via FastAPI's dependency_overrides,
    replacing the `get_container` dependency that every router uses.
    """
    mock_container = MockApplicationContainer()

    with (
        patch("main.initialize_container", new=AsyncMock(return_value=mock_container)),
        patch("main.shutdown_container", new=AsyncMock()),
    ):
        from main import create_application
        from src.presentation.api.routers.deps import get_container

        app = create_application()

        # Override the container dependency so routers receive mock_container
        app.dependency_overrides[get_container] = lambda: mock_container

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    # Clean up dependency overrides after each test
    from main import app as global_app
    global_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: GET /health
# ---------------------------------------------------------------------------

def test_health_returns_200(client):
    """Basic health check must return HTTP 200."""
    # Health router mounts at /health with the basic endpoint at /
    # Combined: /health/ (redirect_slashes=False on both router and app)
    response = client.get("/health/")
    assert response.status_code == 200


def test_health_response_has_status_field(client):
    """Response JSON must include a 'status' key."""
    response = client.get("/health/")
    data = response.json()
    assert "status" in data


def test_health_status_is_healthy(client):
    """The status value must be 'healthy'."""
    response = client.get("/health/")
    data = response.json()
    assert data["status"] == "healthy"


def test_health_response_has_timestamp(client):
    """Response must include a timestamp field."""
    response = client.get("/health/")
    data = response.json()
    assert "timestamp" in data


def test_health_does_not_require_auth(client):
    """
    Health endpoint must be accessible without an Authorization header.
    This is a critical invariant — load balancers and uptime monitors call
    /health without credentials.
    """
    # No Authorization header
    response = client.get("/health/")
    assert response.status_code == 200


def test_health_content_type_is_json(client):
    """Response must be application/json."""
    response = client.get("/health/")
    assert "application/json" in response.headers["content-type"]


# ---------------------------------------------------------------------------
# Tests: GET /health/live (liveness probe — no container dependency)
# ---------------------------------------------------------------------------

def test_liveness_returns_200(client):
    """Liveness probe must always return 200 while the process is alive."""
    response = client.get("/health/live")
    assert response.status_code == 200


def test_liveness_has_alive_field(client):
    """Liveness response must include 'alive' key set to True."""
    response = client.get("/health/live")
    data = response.json()
    assert "alive" in data
    assert data["alive"] is True
