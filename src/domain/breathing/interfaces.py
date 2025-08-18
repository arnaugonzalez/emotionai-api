from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID


class IBreathingSessionRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID, limit: Optional[int] = None, days_back: Optional[int] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def save(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_session_analytics(self, user_id: UUID) -> Dict[str, Any]:
        pass


