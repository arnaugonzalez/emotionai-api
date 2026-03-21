"""
Breathing Router

Endpoints for breathing sessions and patterns.
"""

from datetime import datetime
from typing import Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from .deps import get_container
from ...dependencies import get_current_user_id
from ....infrastructure.container import ApplicationContainer
from ....infrastructure.database.models import BreathingSessionModel, BreathingPatternModel
from ..validators.data_validators import (
    validate_breathing_session,
    validate_breathing_pattern,
)
from .ws import broadcast_calendar_event


router = APIRouter(redirect_slashes=False)


def _handle_db_error(e: Exception, operation: str, entity: str):
    if "foreign key constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid reference in {entity} data")
    if "unique constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{entity.title()} already exists")
    if "not null constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required fields in {entity} data")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error {operation} {entity}")


# Sessions
@router.get("/breathing_sessions/")
async def get_breathing_sessions(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    try:
        db = container.database
        async with db.get_session() as session:
            result = await session.execute(
                select(BreathingSessionModel)
                .where(BreathingSessionModel.user_id == user_id)
                .order_by(BreathingSessionModel.created_at.desc())
            )
            rows = result.scalars().all()
            data = [{
                "id": str(bs.id),
                "pattern": bs.pattern_name,
                "rating": float(bs.effectiveness_rating or 3.0),
                "comment": bs.notes or "",
                "created_at": bs.created_at.isoformat(),
            } for bs in rows]
            return [validate_breathing_session(item) for item in data]
    except Exception as e:
        _handle_db_error(e, "retrieving", "breathing sessions")


@router.post("/breathing_sessions/")
async def create_breathing_session(
    session_body: Dict[str, Any],
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    try:
        db = container.database
        async with db.get_session() as session:
            # Validate rating and description
            rating_val = session_body.get("rating")
            if rating_val is not None:
                try:
                    rating_val = float(rating_val)
                except (TypeError, ValueError):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rating must be a number")
                if rating_val < 1 or rating_val > 5:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rating must be between 1 and 5")
            comment_val = session_body.get("comment")
            if comment_val is not None and len(str(comment_val)) > 200:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="comment must be at most 200 characters")
            model = BreathingSessionModel(
                id=uuid4(),
                user_id=user_id,
                pattern_name=session_body.get("pattern", "Basic Breathing"),
                duration_minutes=session_body.get("duration_minutes", 5),
                completed=session_body.get("completed", True),
                effectiveness_rating=int(rating_val) if rating_val is not None else None,
                notes=comment_val,
                session_data={"source": "flutter_app", "original_data": session_body},
                tags=[],
                tag_confidence=None,
                processed_for_tags=False,
                started_at=datetime.now(),
                completed_at=datetime.now() if session_body.get("completed", True) else None,
            )
            session.add(model)
            await session.commit()
            # Notify calendar listeners
            await broadcast_calendar_event(
                "breathing_session.created",
                {
                    "id": str(model.id),
                    "user_id": str(user_id),
                    "created_at": model.created_at.isoformat(),
                },
            )
            return {
                "id": str(model.id),
                "pattern": model.pattern_name,
                "rating": float(model.effectiveness_rating or 3.0),
                "comment": model.notes or "",
                "created_at": model.created_at.isoformat(),
                "status": "saved",
            }
    except Exception as e:
        _handle_db_error(e, "creating", "breathing session")


# Patterns
@router.get("/breathing_patterns/")
async def get_breathing_patterns(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    try:
        db = container.database
        async with db.get_session() as session:
            preset_result = await session.execute(
                select(BreathingPatternModel)
                .where(BreathingPatternModel.is_preset == True)
                .where(BreathingPatternModel.is_active == True)
                .order_by(BreathingPatternModel.name)
            )
            preset = preset_result.scalars().all()

            user_patterns = []
            if user_id:
                up_result = await session.execute(
                    select(BreathingPatternModel)
                    .where(BreathingPatternModel.user_id == user_id)
                    .where(BreathingPatternModel.is_active == True)
                    .order_by(BreathingPatternModel.name)
                )
                user_patterns = up_result.scalars().all()

            all_patterns = [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "inhale_seconds": p.inhale_seconds,
                    "hold_seconds": p.hold_seconds,
                    "exhale_seconds": p.exhale_seconds,
                    "cycles": p.cycles,
                    "rest_seconds": p.rest_seconds,
                } for p in (list(preset) + list(user_patterns))
            ]

            if not all_patterns:
                all_patterns = [
                    {"id": "preset_1", "name": "4-7-8 Breathing", "inhale_seconds": 4, "hold_seconds": 7, "exhale_seconds": 8, "cycles": 4, "rest_seconds": 0},
                    {"id": "preset_2", "name": "Box Breathing", "inhale_seconds": 4, "hold_seconds": 4, "exhale_seconds": 4, "cycles": 6, "rest_seconds": 0},
                ]

            return [validate_breathing_pattern(p) for p in all_patterns]
    except Exception as e:
        _handle_db_error(e, "retrieving", "breathing patterns")


@router.post("/breathing_patterns/")
async def create_breathing_pattern(
    pattern: Dict[str, Any],
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    try:
        db = container.database
        async with db.get_session() as session:
            # Validate inputs according to app rules (name <= 30, numeric fields <= 99)
            name = str(pattern.get("name", "Custom Pattern"))
            if len(name) > 30:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name must be at most 30 characters")
            def _as_int(key: str, default: int) -> int:
                try:
                    return int(pattern.get(key, default))
                except (TypeError, ValueError):
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{key} must be an integer")
            inhale = _as_int("inhale_seconds", 4)
            hold = _as_int("hold_seconds", 0)
            exhale = _as_int("exhale_seconds", 4)
            cycles = _as_int("cycles", 4)
            rest = _as_int("rest_seconds", 0)
            if inhale < 1 or inhale > 99:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="inhale_seconds must be between 1 and 99")
            if hold < 0 or hold > 99:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="hold_seconds must be between 0 and 99")
            if exhale < 1 or exhale > 99:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="exhale_seconds must be between 1 and 99")
            if cycles < 1 or cycles > 99:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="cycles must be between 1 and 99")
            if rest < 0 or rest > 99:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="rest_seconds must be between 0 and 99")
            model = BreathingPatternModel(
                id=uuid4(),
                user_id=user_id,
                name=name,
                inhale_seconds=inhale,
                hold_seconds=hold,
                exhale_seconds=exhale,
                cycles=cycles,
                rest_seconds=rest,
                description=pattern.get("description"),
                is_preset=False,
                is_active=True,
                tags=[],
                tag_confidence=None,
                processed_for_tags=False,
            )
            session.add(model)
            await session.commit()
            return {
                "id": str(model.id),
                "name": model.name,
                "inhale_seconds": model.inhale_seconds,
                "hold_seconds": model.hold_seconds,
                "exhale_seconds": model.exhale_seconds,
                "cycles": model.cycles,
                "rest_seconds": model.rest_seconds,
                "status": "saved",
            }
    except Exception as e:
        _handle_db_error(e, "creating", "breathing pattern")


