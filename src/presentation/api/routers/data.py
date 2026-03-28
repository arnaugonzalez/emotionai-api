"""
Data Router

Endpoints for custom emotions and related simple data operations used by the app.
"""

from typing import Dict, Any, List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from .deps import get_container
from ...dependencies import get_current_user_id
from ....infrastructure.container import ApplicationContainer
from ....infrastructure.database.models import CustomEmotionModel
from ..validators.data_validators import validate_custom_emotion


router = APIRouter(redirect_slashes=False)


def _handle_db_error(e: Exception, operation: str, entity: str):
    if "foreign key constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid reference in {entity} data")
    if "unique constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{entity.title()} already exists")
    if "not null constraint" in str(e).lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing required fields in {entity} data")
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error {operation} {entity}")


@router.get("/custom_emotions/")
async def get_custom_emotions(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    try:
        db = container.database
        async with db.get_session() as session:
            result = await session.execute(
                select(CustomEmotionModel)
                .where(CustomEmotionModel.user_id == user_id)
                .where(CustomEmotionModel.is_active == True)
                .order_by(CustomEmotionModel.created_at.desc())
            )
            rows: List[CustomEmotionModel] = result.scalars().all()
            data = [
                {
                    "id": str(ce.id),
                    "name": ce.name,
                    "color": ce.color,
                    "created_at": ce.created_at.isoformat() if ce.created_at else None,
                }
                for ce in rows
            ]
            return [validate_custom_emotion(item) for item in data]
    except Exception as e:
        _handle_db_error(e, "retrieving", "custom emotions")


@router.post("/custom_emotions/")
async def create_custom_emotion(
    payload: Dict[str, Any],
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    try:
        name = payload.get("name")
        color = payload.get("color")
        description = payload.get("description")
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required")
        if len(str(name)) > 30:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name must be at most 30 characters")
        if color is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="color is required")
        # Validate color range according to Flutter Color integer (32-bit ARGB)
        try:
            color_int = int(color)
        except (TypeError, ValueError):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="color must be an integer")
        if color_int < 0 or color_int > 0xFFFFFFFF:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="color integer out of range")

        db = container.database
        async with db.get_session() as session:
            # Enforce uniqueness per user + name (constraint also exists in DB)
            existing = await session.execute(
                select(CustomEmotionModel)
                .where(CustomEmotionModel.user_id == user_id)
                .where(CustomEmotionModel.name == name)
            )
            if existing.scalar_one_or_none() is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Custom emotion already exists")

            model = CustomEmotionModel(
                id=uuid4(),
                user_id=user_id,
                name=str(name),
                color=color_int,
                description=str(description) if description else None,
                is_active=True,
                usage_count=0,
                tags=[],
                tag_confidence=None,
                processed_for_tags=False,
            )
            session.add(model)
            await session.commit()

            return validate_custom_emotion(
                {
                    "id": str(model.id),
                    "name": model.name,
                    "color": model.color,
                    "created_at": model.created_at.isoformat() if model.created_at else None,
                }
            )
    except HTTPException:
        raise
    except Exception as e:
        _handle_db_error(e, "creating", "custom emotion")


@router.delete("/custom_emotions/{emotion_id}", status_code=204)
async def delete_custom_emotion(
    emotion_id: str,
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    db = container.database
    async with db.get_session() as session:
        try:
            emotion_uuid = UUID(emotion_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid emotion id")
        result = await session.execute(
            select(CustomEmotionModel).where(
                CustomEmotionModel.id == emotion_uuid,
                CustomEmotionModel.user_id == user_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Custom emotion not found")
        await session.delete(record)
        await session.commit()


@router.put("/custom_emotions/{emotion_id}")
async def update_custom_emotion(
    emotion_id: str,
    body: Dict[str, Any],
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container),
):
    """Update an existing custom emotion (used by offline sync UPDATE operations)."""
    db = container.database
    async with db.get_session() as session:
        try:
            emotion_uuid = UUID(emotion_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid emotion id")

        result = await session.execute(
            select(CustomEmotionModel).where(
                CustomEmotionModel.id == emotion_uuid,
                CustomEmotionModel.user_id == user_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise HTTPException(status_code=404, detail="Custom emotion not found")

        if "name" in body:
            name = str(body["name"])
            if len(name) > 30:
                raise HTTPException(status_code=400, detail="name must be at most 30 characters")
            record.name = name
        if "color" in body:
            try:
                color_int = int(body["color"])
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="color must be an integer")
            if color_int < 0 or color_int > 0xFFFFFFFF:
                raise HTTPException(status_code=400, detail="color integer out of range")
            record.color = color_int

        await session.commit()

        return validate_custom_emotion({
            "id": str(record.id),
            "name": record.name,
            "color": record.color,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        })
