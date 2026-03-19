"""
Integration tests for /v1/api/auth/* endpoints.

These tests use FastAPI's TestClient with a fully mocked ApplicationContainer.
No real database, Redis, or OpenAI calls are made.

Endpoints covered:
  POST /v1/api/auth/register  — new user registration
  POST /v1/api/auth/login     — user login, returns access_token
  POST /v1/api/auth/refresh   — access token refresh
"""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import MockApplicationContainer

# A sentinel hash used in tests — not real bcrypt, just a recognisable string
_FAKE_HASH = "$test$fakehash$for$integration$tests"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REGISTER_URL = "/v1/api/auth/register"
_LOGIN_URL = "/v1/api/auth/login"
_REFRESH_URL = "/v1/api/auth/refresh"

VALID_EMAIL = "test@example.com"
VALID_PASSWORD = "S3cr3tP@ss"


def _make_db_session_mock(user_row=None):
    """
    Build a mock for container.database.get_session() that returns an async
    context manager yielding a mock SQLAlchemy session.

    user_row: if None, simulates "user not found" (scalar_one_or_none → None).
              otherwise, it is returned as-is from scalar_one_or_none().
    """
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user_row

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()

    @asynccontextmanager
    async def _get_session():
        yield mock_session

    return _get_session


def _make_user_row(
    user_id=None,
    email=VALID_EMAIL,
    first_name="Test",
    last_name="User",
    is_verified=False,
):
    """
    Create a mock ORM user row compatible with auth.py expectations.

    We store _FAKE_HASH as the hashed_password. The test fixture patches
    pwd_context.verify so it returns True when comparing VALID_PASSWORD
    against _FAKE_HASH (avoiding real bcrypt which is broken in this env).
    """
    user = MagicMock()
    user.id = user_id or uuid.uuid4()
    user.email = email
    user.hashed_password = _FAKE_HASH
    user.first_name = first_name
    user.last_name = last_name
    user.is_verified = is_verified
    return user


# ---------------------------------------------------------------------------
# Shared fixture: test client with mocked container
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """
    TestClient fixture.

    Patches:
    - initialize_container / shutdown_container: prevent lifespan from
      connecting to real PostgreSQL/Redis/OpenAI
    - src.presentation.api.routers.auth.pwd_context.hash: returns _FAKE_HASH
      (the real passlib+bcrypt is version-incompatible in this environment)
    - src.presentation.api.routers.auth.pwd_context.verify: returns True when
      the password is VALID_PASSWORD (simulates a correct credential check)

    The mock container is injected via FastAPI dependency_overrides.
    """
    mock_container = MockApplicationContainer()

    def _fake_hash(secret):
        return _FAKE_HASH

    def _fake_verify(secret, hashed):
        # In tests: correct password is VALID_PASSWORD, anything else is wrong
        return secret == VALID_PASSWORD

    with (
        patch("main.initialize_container", new=AsyncMock(return_value=mock_container)),
        patch("main.shutdown_container", new=AsyncMock()),
        patch("src.presentation.api.routers.auth.pwd_context.hash", side_effect=_fake_hash),
        patch("src.presentation.api.routers.auth.pwd_context.verify", side_effect=_fake_verify),
    ):
        from main import create_application
        from src.presentation.api.routers.deps import get_container

        app = create_application()
        app.dependency_overrides[get_container] = lambda: mock_container

        with TestClient(app, raise_server_exceptions=True) as c:
            yield c, mock_container

        app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests: POST /v1/api/auth/register
# ---------------------------------------------------------------------------

class TestRegister:

    def test_register_returns_200_for_valid_data(self, client):
        """
        Register with a valid email + password.
        Simulates 'user not found' so a new account is created.
        Returns 200 with access_token, refresh_token, and user fields.
        """
        http, container = client
        # User does not exist yet → scalar_one_or_none returns None
        container.database.get_session = _make_db_session_mock(user_row=None)

        response = http.post(
            _REGISTER_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == VALID_EMAIL

    def test_register_returns_existing_user_token_if_email_taken(self, client):
        """
        Register with an already-existing email.
        The router re-uses the existing user row (no 409) and returns tokens.
        This is the current register semantics in auth.py.
        """
        http, container = client
        existing_user = _make_user_row()
        container.database.get_session = _make_db_session_mock(user_row=existing_user)

        response = http.post(
            _REGISTER_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == VALID_EMAIL

    def test_register_returns_400_for_missing_email(self, client):
        """
        Missing email field → router raises HTTP 400 before touching the DB.
        (Auth router validates manually via `payload.get()`, not Pydantic,
        so the error is 400 Bad Request, not 422 Unprocessable Entity.)
        """
        http, container = client
        response = http.post(_REGISTER_URL, json={"password": VALID_PASSWORD})
        assert response.status_code == 400

    def test_register_returns_400_for_missing_password(self, client):
        """Missing password → HTTP 400."""
        http, container = client
        response = http.post(_REGISTER_URL, json={"email": VALID_EMAIL})
        assert response.status_code == 400

    def test_register_returns_400_for_empty_body(self, client):
        """Completely empty payload → HTTP 400 (no email)."""
        http, container = client
        response = http.post(_REGISTER_URL, json={})
        assert response.status_code == 400

    def test_register_response_includes_expires_in(self, client):
        """Response must include token expiry metadata."""
        http, container = client
        container.database.get_session = _make_db_session_mock(user_row=None)

        response = http.post(
            _REGISTER_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "expires_in" in data
        assert isinstance(data["expires_in"], int)
        assert data["expires_in"] > 0


# ---------------------------------------------------------------------------
# Tests: POST /v1/api/auth/login
# ---------------------------------------------------------------------------

class TestLogin:

    def test_login_returns_access_token_for_valid_credentials(self, client):
        """
        Login with correct email + password.
        Response must contain access_token, refresh_token, token_type, user.
        """
        http, container = client
        user_row = _make_user_row()
        container.database.get_session = _make_db_session_mock(user_row=user_row)

        response = http.post(
            _LOGIN_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

    def test_login_returns_401_for_wrong_password(self, client):
        """Wrong password → HTTP 401 Unauthorized."""
        http, container = client
        user_row = _make_user_row()  # password hash for VALID_PASSWORD
        container.database.get_session = _make_db_session_mock(user_row=user_row)

        response = http.post(
            _LOGIN_URL,
            json={"email": VALID_EMAIL, "password": "wrongpassword"},
        )
        assert response.status_code == 401
        assert "invalid credentials" in response.json().get("detail", "")

    def test_login_returns_401_for_unknown_user(self, client):
        """Email not found in DB → HTTP 401 (router checks user is None)."""
        http, container = client
        container.database.get_session = _make_db_session_mock(user_row=None)

        response = http.post(
            _LOGIN_URL,
            json={"email": "nobody@example.com", "password": VALID_PASSWORD},
        )
        assert response.status_code == 401

    def test_login_returns_400_for_missing_email(self, client):
        """Missing email → HTTP 400."""
        http, container = client
        response = http.post(_LOGIN_URL, json={"password": VALID_PASSWORD})
        assert response.status_code == 400

    def test_login_returns_400_for_missing_password(self, client):
        """Missing password → HTTP 400."""
        http, container = client
        response = http.post(_LOGIN_URL, json={"email": VALID_EMAIL})
        assert response.status_code == 400

    def test_login_response_user_matches_stored_email(self, client):
        """User field in login response must echo back the stored email."""
        http, container = client
        user_row = _make_user_row()
        container.database.get_session = _make_db_session_mock(user_row=user_row)

        response = http.post(
            _LOGIN_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == VALID_EMAIL

    def test_login_access_token_is_nonempty_string(self, client):
        """access_token must be a non-empty string (JWT format not validated here)."""
        http, container = client
        user_row = _make_user_row()
        container.database.get_session = _make_db_session_mock(user_row=user_row)

        response = http.post(
            _LOGIN_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        data = response.json()
        token = data.get("access_token", "")
        assert isinstance(token, str) and len(token) > 20


# ---------------------------------------------------------------------------
# Tests: POST /v1/api/auth/refresh
# ---------------------------------------------------------------------------

class TestRefresh:

    def test_refresh_returns_new_access_token(self, client):
        """
        A valid refresh token (obtained from a login) must yield a new
        access_token without requiring DB access.
        """
        http, container = client

        # First: log in to get a real refresh token
        user_row = _make_user_row()
        container.database.get_session = _make_db_session_mock(user_row=user_row)
        login_resp = http.post(
            _LOGIN_URL,
            json={"email": VALID_EMAIL, "password": VALID_PASSWORD},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        # Then: exchange the refresh token for a new access token
        response = http.post(_REFRESH_URL, json={"refresh_token": refresh_token})
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_returns_401_for_invalid_token(self, client):
        """An invalid refresh token must return HTTP 401."""
        http, _ = client
        response = http.post(_REFRESH_URL, json={"refresh_token": "not.a.valid.token"})
        assert response.status_code == 401
