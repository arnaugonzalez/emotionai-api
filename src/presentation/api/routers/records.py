"""
Records Router

Endpoints for emotional records.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID, uuid4
import hashlib
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, cast, String

from passlib.context import CryptContext

from .deps import get_container
from ...dependencies import get_current_user_id
from ....infrastructure.container import ApplicationContainer
from ....infrastructure.database.models import EmotionalRecordModel, CustomEmotionModel
from ....infrastructure.tasks.notification_tasks import notify_new_record
from ..validators.data_validators import validate_emotional_record
from .ws import broadcast_calendar_event

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
logger = logging.getLogger(__name__)


router = APIRouter(redirect_slashes=False)


def _handle_db_error(e: Exception, operation: str):
    if "foreign key constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reference in emotional record data")
    if "unique constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Emotional record already exists")
    if "not null constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing required fields in emotional record data")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error {operation} emotional records")


def _enqueue_record_notification(record_id: str, user_id: str) -> None:
    try:
        notify_new_record.delay(record_id, user_id)
    except Exception:
        logger.exception(
            "Failed to enqueue notify_new_record task",
            extra={"record_id": record_id, "user_id": user_id},
        )


async def _check_duplicate_record(
    session,
    user_id: UUID,
    emotion: str,
    description: str,
    custom_emotion_name: str = None,
    time_window_minutes: int = 5
) -> bool:
    """
    Check if a similar emotional record exists within the specified time window.
    
    Args:
        session: Database session
        user_id: User ID
        emotion: Emotion name
        description: Description text
        custom_emotion_name: Custom emotion name if applicable
        time_window_minutes: Time window in minutes to check for duplicates
        
    Returns:
        True if duplicate found, False otherwise
    """
    try:
        # Calculate time window
        cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
        
        # Build query based on whether it's a custom emotion or standard emotion
        if custom_emotion_name:
            # For custom emotions, check by custom emotion name and description similarity
            query = select(EmotionalRecordModel).where(
                and_(
                    EmotionalRecordModel.user_id == user_id,
                    EmotionalRecordModel.recorded_at >= cutoff_time,
                    cast(EmotionalRecordModel.context_data['custom_emotion_name'], String) == custom_emotion_name
                )
            )
        else:
            # For standard emotions, check by emotion name and description similarity
            query = select(EmotionalRecordModel).where(
                and_(
                    EmotionalRecordModel.user_id == user_id,
                    EmotionalRecordModel.recorded_at >= cutoff_time,
                    EmotionalRecordModel.emotion == emotion
                )
            )
        
        result = await session.execute(query)
        records = result.scalars().all()
        
        if not records:
            return False
        
        # Check for exact duplicates first
        for record in records:
            record_desc = record.notes or ""
            if record_desc.lower().strip() == description.lower().strip():
                return True
        
        # Check for very similar descriptions using fuzzy matching
        # Simple similarity check: if descriptions are 80% similar, consider them duplicates
        for record in records:
            record_desc = record.notes or ""
            similarity = _calculate_text_similarity(record_desc.lower().strip(), description.lower().strip())
            if similarity > 0.8:
                return True
        
        return False
        
    except Exception as e:
        # Log error but don't block the request
        print(f"Error checking for duplicates: {e}")
        return False


def _calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate text similarity using Levenshtein distance.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score between 0 and 1
    """
    if text1 == text2:
        return 1.0
    
    if not text1 or not text2:
        return 0.0
    
    # Simple Levenshtein distance implementation
    def levenshtein_distance(s1: str, s2: str) -> int:
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    distance = levenshtein_distance(text1, text2)
    max_length = max(len(text1), len(text2))
    
    return 1.0 - (distance / max_length)


@router.get("/emotional_records/")
async def get_emotional_records(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    try:
        db = container.database
        async with db.get_session() as session:
            # Validate user exists (dev-mode: accept provided UUID)
            result = await session.execute(
                select(EmotionalRecordModel)
                .where(EmotionalRecordModel.user_id == user_id)
                .order_by(EmotionalRecordModel.recorded_at.desc())
            )
            rows = result.scalars().all()

            data = []
            for er in rows:
                context = er.context_data or {}
                data.append({
                    "id": str(er.id),
                    "source": context.get("source", "database"),
                    "emotion": er.emotion,
                    "intensity": er.intensity,
                    "description": er.notes or "",
                    "created_at": er.recorded_at.isoformat(),
                    "color": context.get("color"),
                    "custom_emotion_name": context.get("custom_emotion_name"),
                    "custom_emotion_color": context.get("custom_emotion_color"),
                })

            return [validate_emotional_record(item) for item in data]
    except Exception as e:
        _handle_db_error(e, "retrieving")


@router.post("/emotional_records/")
async def create_emotional_record(
    record: Dict[str, Any],
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    try:
        db = container.database
        async with db.get_session() as session:
            # Enforce description length (home screen input) <= 700
            description = record.get("description", "")
            if description is not None and len(str(description)) > 700:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="description must be at most 700 characters")
            # Check for duplicate records before creating
            emotion = record.get("emotion", "neutral")
            custom_emotion_name = record.get("custom_emotion_name")
            
            # Check for duplicates (ignore when description is empty)
            is_duplicate = await _check_duplicate_record(
                session=session,
                user_id=user_id,
                emotion=emotion,
                description=description or "",
                custom_emotion_name=custom_emotion_name,
                time_window_minutes=5
            )
            
            if is_duplicate and (description or custom_emotion_name):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Similar emotional record already exists within the last 5 minutes",
                        "code": "DUPLICATE_RECORD",
                        "suggestion": "Please wait a few minutes or modify your input to avoid duplicates"
                    }
                )
            
            # Ensure user exists, or create a lightweight dev placeholder if not
            # In production, this should be replaced with real auth/user lookup
            from ....infrastructure.database.models import UserModel
            from sqlalchemy import select as _select
            user_row = await session.execute(_select(UserModel).where(UserModel.id == user_id))
            user_obj = user_row.scalar_one_or_none()
            if user_obj is None:
                # Create minimal placeholder
                user_obj = UserModel(
                    id=user_id,
                    email=f"dev+{str(user_id)}@example.com",
                    hashed_password=pwd_context.hash("placeholder"),
                    first_name="Dev",
                    last_name="User",
                    is_active=True,
                    is_verified=False,
                )
                session.add(user_obj)
                await session.flush()
            model = EmotionalRecordModel(
                id=uuid4(),
                user_id=user_id,
                emotion=emotion,
                intensity=max(1, min(10, int(record.get("intensity") or 5))),
                triggers=record.get("triggers", []),
                notes=description,
                context_data={
                    "source": record.get("source", "flutter_app"),
                    "color": record.get("color"),
                    "custom_emotion_name": custom_emotion_name,
                    "custom_emotion_color": record.get("custom_emotion_color"),
                },
                tags=[],
                tag_confidence=None,
                processed_for_tags=False,
                recorded_at=datetime.now(),
            )
            session.add(model)
            await session.commit()
            _enqueue_record_notification(str(model.id), str(user_id))
            # Notify listeners
            await broadcast_calendar_event(
                "emotional_record.created",
                {
                    "id": str(model.id),
                    "user_id": str(user_id),
                    "created_at": model.recorded_at.isoformat(),
                },
            )

            return {
                "id": str(model.id),
                "emotion": model.emotion,
                "intensity": model.intensity,
                "description": model.notes,
                "created_at": model.recorded_at.isoformat(),
                "source": "database",
                "status": "saved",
            }
    except HTTPException:
        raise
    except Exception as e:
        _handle_db_error(e, "creating")


@router.post("/emotional_records/from_custom_emotion")
async def create_record_from_custom_emotion(
    body: Dict[str, Any],
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container),
):
    """Create an emotional record tied to a custom emotion for immediate calendar refresh."""
    try:
        db = container.database
        async with db.get_session() as session:
            name = body.get("custom_emotion_name")
            color = body.get("custom_emotion_color")
            intensity = body.get("intensity")
            notes = body.get("description")
            if not name:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="custom_emotion_name is required")
            if color is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="custom_emotion_color is required")

            # Check for duplicate records before creating
            is_duplicate = await _check_duplicate_record(
                session=session,
                user_id=user_id,
                emotion=str(name),
                description=notes or "",
                custom_emotion_name=str(name),
                time_window_minutes=5
            )

            if is_duplicate:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Similar emotional record already exists within the last 5 minutes",
                        "code": "DUPLICATE_RECORD",
                        "suggestion": "Please wait a few minutes or modify your input to avoid duplicates"
                    }
                )

            # Ensure the custom emotion exists for the user; if not, create it quickly
            ce_res = await session.execute(
                select(CustomEmotionModel)
                .where(CustomEmotionModel.user_id == user_id)
                .where(CustomEmotionModel.name == name)
            )
            ce = ce_res.scalar_one_or_none()
            if ce is None:
                ce = CustomEmotionModel(
                    id=uuid4(),
                    user_id=user_id,
                    name=str(name),
                    color=int(color),
                    is_active=True,
                    usage_count=0,
                    tags=[],
                    tag_confidence=None,
                    processed_for_tags=False,
                )
                session.add(ce)
                await session.flush()

            # Create the emotional record immediately
            model = EmotionalRecordModel(
                id=uuid4(),
                user_id=user_id,
                emotion=str(name),
                intensity=max(1, min(10, int(intensity or 5))) if intensity is not None else 5,
                triggers=[],
                notes=notes or "",
                context_data={
                    "source": body.get("source", "flutter_app"),
                    "color": int(color),
                    "custom_emotion_name": str(name),
                    "custom_emotion_color": int(color),
                },
                tags=[],
                tag_confidence=None,
                processed_for_tags=False,
                recorded_at=datetime.now(),
            )
            session.add(model)
            await session.commit()
            # Broadcast update
            await broadcast_calendar_event(
                "emotional_record.created",
                {
                    "id": str(model.id),
                    "user_id": str(user_id),
                    "created_at": model.recorded_at.isoformat(),
                },
            )

            return validate_emotional_record(
                {
                    "id": str(model.id),
                    "source": "database",
                    "emotion": model.emotion,
                    "intensity": model.intensity,
                    "description": model.notes,
                    "created_at": model.recorded_at.isoformat(),
                    "color": int(color),
                    "custom_emotion_name": str(name),
                    "custom_emotion_color": int(color),
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        _handle_db_error(e, "creating")


@router.delete("/emotional_records/{record_id}", status_code=204)
async def delete_emotional_record(
    record_id: str,
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    db = container.database
    async with db.get_session() as session:
        try:
            record_uuid = UUID(record_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid record id")
        result = await session.execute(
            select(EmotionalRecordModel).where(
                EmotionalRecordModel.id == record_uuid,
                EmotionalRecordModel.user_id == user_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")
        await session.delete(record)
        await session.commit()


@router.put("/emotional_records/{record_id}")
async def update_emotional_record(
    record_id: str,
    body: Dict[str, Any],
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container),
):
    """Update an existing emotional record (used by offline sync UPDATE operations)."""
    db = container.database
    async with db.get_session() as session:
        try:
            record_uuid = UUID(record_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid record id")

        result = await session.execute(
            select(EmotionalRecordModel).where(
                EmotionalRecordModel.id == record_uuid,
                EmotionalRecordModel.user_id == user_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Record not found")

        # Apply mutable fields
        if "emotion" in body:
            record.emotion = body["emotion"]
        if "intensity" in body:
            record.intensity = max(1, min(10, int(body["intensity"])))
        if "description" in body:
            desc = body["description"]
            if desc is not None and len(str(desc)) > 700:
                raise HTTPException(status_code=400, detail="description must be at most 700 characters")
            record.notes = desc
        if "triggers" in body:
            record.triggers = body["triggers"]

        # Merge context_data fields
        ctx = record.context_data or {}
        for key in ("source", "color", "custom_emotion_name", "custom_emotion_color"):
            if key in body:
                ctx[key] = body[key]
        record.context_data = ctx

        await session.commit()

        return {
            "id": str(record.id),
            "emotion": record.emotion,
            "intensity": record.intensity,
            "description": record.notes,
            "created_at": record.recorded_at.isoformat(),
            "source": (record.context_data or {}).get("source", "database"),
            "status": "updated",
        }
