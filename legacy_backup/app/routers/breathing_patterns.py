from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=schemas.BreathingPattern)
def create_breathing_pattern(
    pattern: schemas.BreathingPatternCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_breathing_pattern(db=db, pattern=pattern, user_id=current_user.id)

@router.get("/", response_model=List[schemas.BreathingPattern])
def read_breathing_patterns(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    patterns = crud.get_breathing_patterns(db, skip=skip, limit=limit)
    return patterns