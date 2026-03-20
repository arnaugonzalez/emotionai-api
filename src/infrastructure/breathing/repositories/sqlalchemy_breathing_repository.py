"""SQLAlchemy Breathing Session Repository (feature-scoped)"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_

from ....domain.breathing.interfaces import IBreathingSessionRepository
from ....infrastructure.database.models import BreathingSessionModel


def _model_to_dict(model: BreathingSessionModel) -> Dict[str, Any]:
    return {
        "id": str(model.id),
        "user_id": str(model.user_id),
        "pattern_name": model.pattern_name,
        "duration_minutes": model.duration_minutes,
        "completed": model.completed,
        "effectiveness_rating": model.effectiveness_rating,
        "notes": model.notes or "",
        "started_at": model.started_at,
        "completed_at": model.completed_at,
        "tags": model.tags,
    }


class SqlAlchemyBreathingRepository(IBreathingSessionRepository):
    def __init__(self, db_connection):
        self.db = db_connection

    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: Optional[int] = None,
        days_back: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        async with self.db.get_session() as session:
            query = select(BreathingSessionModel).where(
                BreathingSessionModel.user_id == user_id
            ).order_by(BreathingSessionModel.started_at.desc())
            if days_back is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
                query = query.where(BreathingSessionModel.started_at >= cutoff)
            if limit is not None:
                query = query.limit(limit)
            result = await session.execute(query)
            rows = result.scalars().all()
            return [_model_to_dict(r) for r in rows]

    async def save(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.db.get_session() as session:
            model = BreathingSessionModel(**session_data)
            session.add(model)
            await session.flush()
            return _model_to_dict(model)

    async def get_session_analytics(self, user_id: UUID) -> Dict[str, Any]:
        async with self.db.get_session() as session:
            result = await session.execute(
                select(BreathingSessionModel)
                .where(BreathingSessionModel.user_id == user_id)
            )
            rows = result.scalars().all()
            total = len(rows)
            avg_duration = sum(r.duration_minutes for r in rows) / total if total else 0.0
            pattern_counts: Dict[str, int] = {}
            for r in rows:
                pattern_counts[r.pattern_name] = pattern_counts.get(r.pattern_name, 0) + 1
            favorite = sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            return {
                "total_sessions": total,
                "average_duration": round(avg_duration, 1),
                "improvement_trend": "stable",
                "favorite_patterns": [p[0] for p in favorite],
            }
