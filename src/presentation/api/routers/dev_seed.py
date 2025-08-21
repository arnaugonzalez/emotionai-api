"""
Dev Seed Router

Endpoints for loading and resetting preset demo data in development only.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, delete

from .deps import get_container, get_current_user_id
from ....infrastructure.container import ApplicationContainer
from ....infrastructure.config.settings import settings
from ....infrastructure.database.models import (
    UserModel,
    BreathingSessionModel,
    BreathingPatternModel,
    EmotionalRecordModel,
)


router = APIRouter()


def _ensure_dev():
    if not settings.is_development:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dev-only endpoint")


@router.post("/dev/seed/load_preset_data")
async def load_preset_data(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container),
):
    """Insert demo breathing sessions and emotional records across the last 30 days.

    Idempotent via a day-based seed marker in model notes/context (no duplication on rerun).
    """
    _ensure_dev()
    db = container.database
    now = datetime.now()

    # Distribute 10 dates roughly evenly across last 30 days
    day_offsets = [int(i * (30 / 10)) for i in range(10)]
    day_offsets = [min(29, off) for off in day_offsets]
    target_dates = [now - timedelta(days=off) for off in day_offsets]

    patterns: List[Dict[str, Any]] = [
        {"name": "Box Breathing", "inhale_seconds": 4, "hold_seconds": 4, "exhale_seconds": 4, "cycles": 6, "rest_seconds": 0},
        {"name": "4-7-8 Breathing", "inhale_seconds": 4, "hold_seconds": 7, "exhale_seconds": 8, "cycles": 4, "rest_seconds": 0},
        {"name": "Coherent Breathing", "inhale_seconds": 5, "hold_seconds": 0, "exhale_seconds": 5, "cycles": 6, "rest_seconds": 0},
        {"name": "Physiological Sigh", "inhale_seconds": 2, "hold_seconds": 0, "exhale_seconds": 6, "cycles": 6, "rest_seconds": 0},
    ]

    emotions = [
        {"emotion": "calm", "intensity": 6},
        {"emotion": "happy", "intensity": 7},
        {"emotion": "anxious", "intensity": 5},
        {"emotion": "stressed", "intensity": 6},
        {"emotion": "grateful", "intensity": 8},
        {"emotion": "tired", "intensity": 4},
        {"emotion": "focused", "intensity": 7},
        {"emotion": "content", "intensity": 6},
        {"emotion": "overwhelmed", "intensity": 6},
        {"emotion": "hopeful", "intensity": 7},
    ]

    # Default color mapping for standard emotions (Flutter ARGB ints)
    emotion_colors = {
        "calm": 0xFF80CBC4,         # teal lighten-3
        "happy": 0xFFFFEB3B,        # yellow
        "anxious": 0xFFFFB74D,      # orange lighten-1
        "stressed": 0xFFEF5350,     # red lighten-1
        "grateful": 0xFF66BB6A,     # green lighten-1
        "tired": 0xFF90A4AE,        # blueGrey lighten-2
        "focused": 0xFF42A5F5,      # blue lighten-1
        "content": 0xFF9CCC65,      # light green lighten-1
        "overwhelmed": 0xFFAB47BC,  # purple lighten-1
        "hopeful": 0xFF26C6DA,      # cyan lighten-1
    }

    try:
        async with db.get_session() as session:
            # Ensure user exists (dev placeholder allowed)
            res = await session.execute(select(UserModel).where(UserModel.id == user_id))
            user = res.scalar_one_or_none()
            if user is None:
                user = UserModel(
                    id=user_id,
                    email=f"dev+{str(user_id)}@example.com",
                    hashed_password="dev",
                    first_name="Dev",
                    last_name="User",
                    is_active=True,
                    is_verified=False,
                )
                session.add(user)
                await session.flush()

            # Ensure preset patterns exist (global presets is_preset=True)
            existing_presets = await session.execute(
                select(BreathingPatternModel).where(BreathingPatternModel.is_preset == True)
            )
            existing_names = {p.name for p in existing_presets.scalars().all()}
            for p in patterns:
                if p["name"] not in existing_names:
                    session.add(
                        BreathingPatternModel(
                            user_id=None,
                            name=p["name"],
                            inhale_seconds=p["inhale_seconds"],
                            hold_seconds=p["hold_seconds"],
                            exhale_seconds=p["exhale_seconds"],
                            cycles=p["cycles"],
                            rest_seconds=p["rest_seconds"],
                            description=f"Preset: {p['name']}",
                            is_preset=True,
                            is_active=True,
                            tags=[],
                            processed_for_tags=False,
                        )
                    )

            # Seed breathing sessions idempotently
            created_sessions = 0
            for idx, dt in enumerate(target_dates):
                seed_marker = f"dev_seed:{dt.strftime('%Y-%m-%d')}"
                exists_q = await session.execute(
                    select(BreathingSessionModel)
                    .where(BreathingSessionModel.user_id == user_id)
                    .where(BreathingSessionModel.notes.ilike(f"%{seed_marker}%"))
                )
                if exists_q.scalar_one_or_none() is not None:
                    continue
                pat = patterns[idx % len(patterns)]
                session.add(
                    BreathingSessionModel(
                        id=uuid4(),
                        user_id=user_id,
                        pattern_name=pat["name"],
                        duration_minutes=5 + (idx % 6),
                        completed=True,
                        effectiveness_rating=3 + (idx % 3),
                        notes=f"Seeded session {idx+1}. {seed_marker}",
                        session_data={"source": "dev_seed"},
                        tags=[],
                        tag_confidence=None,
                        processed_for_tags=False,
                        started_at=dt,
                        completed_at=dt + timedelta(minutes=5 + (idx % 6)),
                        created_at=dt,
                    )
                )
                created_sessions += 1

            # Seed emotional records idempotently
            created_records = 0
            for idx, dt in enumerate(target_dates):
                seed_marker = f"dev_seed:{dt.strftime('%Y-%m-%d')}"
                exists_q = await session.execute(
                    select(EmotionalRecordModel)
                    .where(EmotionalRecordModel.user_id == user_id)
                    .where(EmotionalRecordModel.notes.ilike(f"%{seed_marker}%"))
                )
                if exists_q.scalar_one_or_none() is not None:
                    continue
                emo = emotions[idx % len(emotions)]
                session.add(
                    EmotionalRecordModel(
                        id=uuid4(),
                        user_id=user_id,
                        emotion=emo["emotion"],
                        intensity=int(emo["intensity"]),
                        triggers=["seed"],
                        notes=f"Seeded record {idx+1}. {seed_marker}",
                        context_data={
                            "source": "dev_seed",
                            "color": int(emotion_colors.get(emo["emotion"], 0xFF9E9E9E)),
                        },
                        tags=[],
                        tag_confidence=None,
                        processed_for_tags=False,
                        recorded_at=dt,
                        created_at=dt,
                    )
                )
                created_records += 1

            return {
                "status": "ok",
                "created_sessions": created_sessions,
                "created_records": created_records,
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error seeding data: {e}")


@router.post("/dev/seed/reset")
async def reset_dev_seed(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container),
):
    """Delete previously seeded demo data for the given user (dev only)."""
    _ensure_dev()
    db = container.database
    try:
        async with db.get_session() as session:
            # Delete breathing sessions with seed marker
            bs = await session.execute(
                select(BreathingSessionModel.id)
                .where(BreathingSessionModel.user_id == user_id)
                .where(BreathingSessionModel.notes.ilike("%dev_seed:%"))
            )
            bs_ids = [row for row in bs.scalars().all()]
            if bs_ids:
                await session.execute(
                    delete(BreathingSessionModel).where(BreathingSessionModel.id.in_(bs_ids))
                )

            # Delete emotional records with seed marker
            er = await session.execute(
                select(EmotionalRecordModel.id)
                .where(EmotionalRecordModel.user_id == user_id)
                .where(EmotionalRecordModel.notes.ilike("%dev_seed:%"))
            )
            er_ids = [row for row in er.scalars().all()]
            if er_ids:
                await session.execute(
                    delete(EmotionalRecordModel).where(EmotionalRecordModel.id.in_(er_ids))
                )

            return {
                "status": "ok",
                "deleted_sessions": len(bs_ids),
                "deleted_records": len(er_ids),
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error resetting seed data: {e}")


