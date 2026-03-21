"""SQLAlchemy Emotional Record Repository (feature-scoped)"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from ....domain.records.interfaces import IEmotionalRecordRepository
from ....infrastructure.database.models import EmotionalRecordModel


def _model_to_dict(model: EmotionalRecordModel) -> Dict[str, Any]:
    return {
        "id": str(model.id),
        "user_id": str(model.user_id),
        "emotion": model.emotion,
        "intensity": model.intensity,
        "triggers": model.triggers,
        "notes": model.notes or "",
        "recorded_at": model.recorded_at,
        "tags": model.tags,
        "tag_confidence": model.tag_confidence,
        "context_data": model.context_data,
        "created_at": model.created_at,
    }


class SqlAlchemyEmotionalRepository(IEmotionalRecordRepository):
    def __init__(self, db_connection):
        self.db = db_connection

    async def get_by_user_id(
        self,
        user_id: UUID,
        limit: Optional[int] = None,
        days_back: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        async with self.db.get_session() as session:
            query = select(EmotionalRecordModel).where(
                EmotionalRecordModel.user_id == user_id
            ).order_by(EmotionalRecordModel.recorded_at.desc())
            if days_back is not None:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
                query = query.where(EmotionalRecordModel.recorded_at >= cutoff)
            if limit is not None:
                query = query.limit(limit)
            result = await session.execute(query)
            rows = result.scalars().all()
            return [_model_to_dict(r) for r in rows]

    async def save(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.db.get_session() as session:
            model = EmotionalRecordModel(**record_data)
            session.add(model)
            await session.flush()
            return _model_to_dict(model)

    async def get_emotional_patterns(self, user_id: UUID) -> Dict[str, Any]:
        async with self.db.get_session() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            result = await session.execute(
                select(EmotionalRecordModel)
                .where(and_(
                    EmotionalRecordModel.user_id == user_id,
                    EmotionalRecordModel.recorded_at >= cutoff,
                ))
                .order_by(EmotionalRecordModel.recorded_at.desc())
            )
            rows = result.scalars().all()
            emotion_counts: Dict[str, int] = {}
            for r in rows:
                emotion_counts[r.emotion] = emotion_counts.get(r.emotion, 0) + 1
            dominant = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            return {
                "dominant_emotions": [{"emotion": e, "count": c} for e, c in dominant],
                "mood_trends": emotion_counts,
                "patterns": [],
            }

    async def get_by_user_id_with_user(
        self,
        user_id: UUID,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get emotional records with eagerly loaded user (avoids DetachedInstanceError)"""
        async with self.db.get_session() as session:
            query = (
                select(EmotionalRecordModel)
                .where(EmotionalRecordModel.user_id == user_id)
                .options(selectinload(EmotionalRecordModel.user))
                .order_by(EmotionalRecordModel.recorded_at.desc())
            )
            if limit is not None:
                query = query.limit(limit)
            result = await session.execute(query)
            rows = result.scalars().all()
            return [_model_to_dict(r) for r in rows]

    async def get_records_by_date_range(self, user_id: UUID, start_date, end_date) -> List[Dict[str, Any]]:
        try:
            async with self.db.get_session() as session:
                result = await session.execute(
                    select(EmotionalRecordModel)
                    .where(
                        and_(
                            EmotionalRecordModel.user_id == user_id,
                            EmotionalRecordModel.recorded_at >= start_date,
                            EmotionalRecordModel.recorded_at <= end_date,
                        )
                    )
                    .order_by(EmotionalRecordModel.recorded_at.desc())
                )
                rows = result.scalars().all()
                records: List[Dict[str, Any]] = []
                for er in rows:
                    records.append({
                        "id": str(er.id),
                        "emotion": er.emotion,
                        "intensity": er.intensity,
                        "description": er.notes or "",
                        "created_at": er.recorded_at,
                    })
                return records
        except Exception:
            return []
