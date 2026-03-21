"""SQLAlchemy Event Repository (feature-scoped)"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, and_

from ....domain.events.interfaces import IEventRepository
from ....domain.events.domain_events import DomainEvent
from ....infrastructure.database.models import DomainEventModel


def _model_to_domain_event(model: DomainEventModel) -> DomainEvent:
    return DomainEvent(
        event_id=str(model.id),
        occurred_at=model.created_at,
        event_type=model.event_type,
    )


class SqlAlchemyEventRepository(IEventRepository):
    def __init__(self, db_connection):
        self.db = db_connection

    async def save_event(self, event: DomainEvent) -> None:
        async with self.db.get_session() as session:
            model = DomainEventModel(
                event_type=event.event_type,
                event_data=event.to_dict(),
                aggregate_id=event.event_id,
                user_id=getattr(event, "user_id", None),
                processed=False,
            )
            session.add(model)
            await session.flush()

    async def get_events_by_user(
        self,
        user_id: UUID,
        event_types: Optional[List[str]] = None,
    ) -> List[DomainEvent]:
        async with self.db.get_session() as session:
            query = (
                select(DomainEventModel)
                .where(DomainEventModel.user_id == user_id)
                .order_by(DomainEventModel.created_at.desc())
            )
            if event_types:
                query = query.where(DomainEventModel.event_type.in_(event_types))
            result = await session.execute(query)
            rows = result.scalars().all()
            return [_model_to_domain_event(r) for r in rows]

    async def get_unprocessed_events(self) -> List[DomainEvent]:
        async with self.db.get_session() as session:
            result = await session.execute(
                select(DomainEventModel)
                .where(DomainEventModel.processed == False)
                .order_by(DomainEventModel.created_at.asc())
            )
            rows = result.scalars().all()
            return [_model_to_domain_event(r) for r in rows]

    async def mark_event_processed(self, event_id: str) -> None:
        async with self.db.get_session() as session:
            result = await session.execute(
                select(DomainEventModel).where(
                    DomainEventModel.aggregate_id == event_id
                )
            )
            model = result.scalar_one_or_none()
            if model:
                model.processed = True
                model.processed_at = datetime.now(timezone.utc)
                await session.flush()
