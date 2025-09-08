from datetime import datetime
from typing import Optional
from uuid import UUID
from ....domain.usage.interfaces import ITokenUsageRepository


class GetMonthlyUsageUseCase:
    def __init__(self, token_usage_repository: ITokenUsageRepository) -> None:
        self.token_usage_repository = token_usage_repository

    async def execute(self, user_id: UUID, year: Optional[int] = None, month: Optional[int] = None) -> int:
        now = datetime.now()
        return await self.token_usage_repository.get_monthly_usage(user_id, year or now.year, month or now.month)


