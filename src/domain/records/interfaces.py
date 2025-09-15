from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID


class IEmotionalRecordRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: UUID, limit: Optional[int] = None, days_back: Optional[int] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def save(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_emotional_patterns(self, user_id: UUID) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def get_records_by_date_range(self, user_id: UUID, start_date, end_date) -> List[Dict[str, Any]]:
        """Return emotional records for a user between start_date and end_date inclusive."""
        pass


