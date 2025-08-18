"""
Token Usage Repository (feature-scoped)

Implements ITokenUsageRepository under infrastructure/usage/repositories.
"""

from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select, extract, func

from ....domain.usage.interfaces import ITokenUsageRepository
from ...database.models import TokenUsageModel


class SqlAlchemyTokenUsageRepository(ITokenUsageRepository):
    def __init__(self, db_connection):
        self.db = db_connection

    async def log_usage(
        self,
        user_id: UUID,
        interaction_type: str,
        total_tokens: int,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
        model: Optional[str] = None,
        data_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        async with self.db.get_session() as session:
            usage = TokenUsageModel(
                user_id=user_id,
                interaction_type=interaction_type,
                model=model,
                data_id=data_id,
                tokens_total=total_tokens,
                tokens_prompt=tokens_prompt,
                tokens_completion=tokens_completion,
                usage_metadata=metadata or {},
            )
            session.add(usage)
            await session.commit()

    async def get_monthly_usage(self, user_id: UUID, year: int, month: int) -> int:
        async with self.db.get_session() as session:
            stmt = (
                select(func.coalesce(func.sum(TokenUsageModel.tokens_total), 0))
                .where(TokenUsageModel.user_id == user_id)
                .where(extract('year', TokenUsageModel.created_at) == year)
                .where(extract('month', TokenUsageModel.created_at) == month)
            )
            result = await session.execute(stmt)
            return int(result.scalar_one() or 0)

    async def get_user_analytics(self, user_id: UUID) -> Dict[str, Any]:  # type: ignore[override]
        return {}

    async def get_system_metrics(self) -> Dict[str, Any]:  # type: ignore[override]
        return {}