from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from uuid import UUID


class IAgentConversationRepository(ABC):
    @abstractmethod
    async def save_conversation(self, user_id: UUID, agent_type: str, conversation_data: Dict[str, Any]) -> str:
        pass

    @abstractmethod
    async def get_conversation_history(self, user_id: UUID, agent_type: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_conversation_summary(self, user_id: UUID, agent_type: str) -> Optional[str]:
        pass


