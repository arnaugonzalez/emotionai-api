from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=schemas.BreathingSessionData)
def create_breathing_session(
    session: schemas.BreathingSessionDataCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_record(db=db, model=models.BreathingSessionData, schema=session, user_id=current_user.id)

@router.get("/", response_model=List[schemas.BreathingSessionData])
def read_breathing_sessions(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    sessions = crud.get_records_by_owner(db, model=models.BreathingSessionData, user_id=current_user.id, skip=skip, limit=limit)
    return sessions