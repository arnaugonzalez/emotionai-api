from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID


class ITokenUsageRepository(ABC):
    @abstractmethod
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
        pass

    @abstractmethod
    async def get_monthly_usage(self, user_id: UUID, year: int, month: int) -> int:
        pass


