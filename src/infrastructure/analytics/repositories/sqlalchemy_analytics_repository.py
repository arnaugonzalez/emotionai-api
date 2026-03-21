"""Analytics Repository (feature-scoped)

Non-token analytics: structured logging of agent interactions.
Token usage is tracked separately via SqlAlchemyTokenUsageRepository.
"""

import json
import logging
from typing import Dict, Any
from uuid import UUID

from ....domain.analytics.interfaces import IAnalyticsRepository

logger = logging.getLogger(__name__)


class SqlAlchemyAnalyticsRepository(IAnalyticsRepository):
    def __init__(self, db_connection):
        self.db = db_connection

    async def save_agent_interaction(
        self, user_id: UUID, agent_type: str, interaction_data: Dict[str, Any]
    ) -> None:
        logger.info(
            "agent_interaction",
            extra={
                "user_id": str(user_id),
                "agent_type": agent_type,
                "interaction_data": json.dumps(interaction_data, default=str),
            },
        )
        return None
