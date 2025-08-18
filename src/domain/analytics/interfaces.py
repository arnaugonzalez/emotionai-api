from abc import ABC, abstractmethod
from typing import Dict, Any
from uuid import UUID


class IAnalyticsRepository(ABC):
    @abstractmethod
    async def save_agent_interaction(self, user_id: UUID, agent_type: str, interaction_data: Dict[str, Any]) -> None:
        pass


