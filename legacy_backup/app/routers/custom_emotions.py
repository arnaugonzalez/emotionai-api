from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=schemas.CustomEmotion)
def create_custom_emotion(
    emotion: schemas.CustomEmotionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_record(db=db, model=models.CustomEmotion, schema=emotion, user_id=current_user.id)

@router.get("/", response_model=List[schemas.CustomEmotion])
def read_custom_emotions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    emotions = crud.get_records_by_owner(db, model=models.CustomEmotion, user_id=current_user.id, skip=skip, limit=limit)
    return emotions