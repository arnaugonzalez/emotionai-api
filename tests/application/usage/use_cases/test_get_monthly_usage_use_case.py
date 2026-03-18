from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from src.application.usage.use_cases.get_monthly_usage_use_case import GetMonthlyUsageUseCase
import src.application.usage.use_cases.get_monthly_usage_use_case as usage_module


@pytest.mark.asyncio
async def test_execute_uses_explicit_year_and_month():
    repo = AsyncMock()
    repo.get_monthly_usage.return_value = 123

    use_case = GetMonthlyUsageUseCase(token_usage_repository=repo)
    user_id = uuid4()

    result = await use_case.execute(user_id=user_id, year=2025, month=2)

    assert result == 123
    repo.get_monthly_usage.assert_awaited_once_with(user_id, 2025, 2)


@pytest.mark.asyncio
async def test_execute_uses_current_date_when_year_month_missing(monkeypatch):
    class FakeDateTime(datetime):
        @classmethod
        def now(cls):
            return cls(2026, 3, 1)

    monkeypatch.setattr(usage_module, "datetime", FakeDateTime)

    repo = AsyncMock()
    repo.get_monthly_usage.return_value = 77
    use_case = GetMonthlyUsageUseCase(token_usage_repository=repo)
    user_id = uuid4()

    result = await use_case.execute(user_id=user_id)

    assert result == 77
    repo.get_monthly_usage.assert_awaited_once_with(user_id, 2026, 3)
