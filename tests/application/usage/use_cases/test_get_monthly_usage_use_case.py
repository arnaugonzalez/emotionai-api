"""
Tests for GetMonthlyUsageUseCase.

Strategy: inject AsyncMock for ITokenUsageRepository — no real DB, no network.
Verify business logic: correct delegation, default year/month, return value passthrough.
"""

from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest

from src.application.usage.use_cases.get_monthly_usage_use_case import GetMonthlyUsageUseCase

USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def make_use_case(repo: AsyncMock | None = None) -> tuple[GetMonthlyUsageUseCase, AsyncMock]:
    """Return a use case wired to a fresh mock repo (or the one provided)."""
    mock_repo = repo if repo is not None else AsyncMock()
    return GetMonthlyUsageUseCase(token_usage_repository=mock_repo), mock_repo


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


async def test_get_monthly_usage_returns_usage_for_valid_user() -> None:
    """Happy path: repo returns a token count, use case passes it through."""
    use_case, mock_repo = make_use_case()
    mock_repo.get_monthly_usage.return_value = 4200

    result = await use_case.execute(user_id=USER_ID, year=2026, month=3)

    assert result == 4200


async def test_get_monthly_usage_returns_zero_for_new_user() -> None:
    """A brand-new user has zero token usage; use case should return 0."""
    use_case, mock_repo = make_use_case()
    mock_repo.get_monthly_usage.return_value = 0

    result = await use_case.execute(user_id=USER_ID, year=2026, month=3)

    assert result == 0


# ---------------------------------------------------------------------------
# Interaction / argument verification
# ---------------------------------------------------------------------------


async def test_get_monthly_usage_calls_repository_with_correct_user_id() -> None:
    """The use case must forward the exact user_id it receives to the repo."""
    use_case, mock_repo = make_use_case()
    mock_repo.get_monthly_usage.return_value = 100
    specific_user = uuid4()

    await use_case.execute(user_id=specific_user, year=2026, month=1)

    mock_repo.get_monthly_usage.assert_called_once_with(specific_user, 2026, 1)


async def test_get_monthly_usage_uses_current_year_and_month_when_not_provided() -> None:
    """When year/month are omitted the use case defaults to the current date."""
    use_case, mock_repo = make_use_case()
    mock_repo.get_monthly_usage.return_value = 50

    fixed_now = datetime(2025, 11, 7)
    with patch(
        "src.application.usage.use_cases.get_monthly_usage_use_case.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now
        await use_case.execute(user_id=USER_ID)

    mock_repo.get_monthly_usage.assert_called_once_with(USER_ID, 2025, 11)


async def test_get_monthly_usage_uses_provided_year_month_over_defaults() -> None:
    """Explicit year/month arguments are used even when 'now' would differ."""
    use_case, mock_repo = make_use_case()
    mock_repo.get_monthly_usage.return_value = 999

    fixed_now = datetime(2025, 6, 1)
    with patch(
        "src.application.usage.use_cases.get_monthly_usage_use_case.datetime"
    ) as mock_dt:
        mock_dt.now.return_value = fixed_now
        result = await use_case.execute(user_id=USER_ID, year=2024, month=12)

    assert result == 999
    mock_repo.get_monthly_usage.assert_called_once_with(USER_ID, 2024, 12)


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


async def test_get_monthly_usage_propagates_repository_exception() -> None:
    """If the repo raises, the use case lets the exception propagate unchanged."""
    use_case, mock_repo = make_use_case()
    mock_repo.get_monthly_usage.side_effect = RuntimeError("DB connection lost")

    with pytest.raises(RuntimeError, match="DB connection lost"):
        await use_case.execute(user_id=USER_ID, year=2026, month=3)


async def test_get_monthly_usage_called_exactly_once_per_execute() -> None:
    """Each call to execute results in exactly one repo call — no double-counting."""
    use_case, mock_repo = make_use_case()
    mock_repo.get_monthly_usage.return_value = 10

    await use_case.execute(user_id=USER_ID, year=2026, month=3)

    assert mock_repo.get_monthly_usage.call_count == 1
