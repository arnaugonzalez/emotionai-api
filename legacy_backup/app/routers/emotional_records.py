from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=schemas.EmotionalRecord)
def create_emotional_record(
    record: schemas.EmotionalRecordCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_record(db=db, model=models.EmotionalRecord, schema=record, user_id=current_user.id)

@router.get("/", response_model=List[schemas.EmotionalRecord])
def read_emotional_records(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    records = crud.get_records_by_owner(db, model=models.EmotionalRecord, user_id=current_user.id, skip=skip, limit=limit)
    return records