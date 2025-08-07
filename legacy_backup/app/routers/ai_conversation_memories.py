from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from .. import crud, models, schemas
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter()

@router.post("/", response_model=schemas.AiConversationMemory)
def create_ai_conversation_memory(
    memory: schemas.AiConversationMemoryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    return crud.create_record(db=db, model=models.AiConversationMemory, schema=memory, user_id=current_user.id)

@router.get("/", response_model=List[schemas.AiConversationMemory])
def read_ai_conversation_memories(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    memories = crud.get_records_by_owner(db, model=models.AiConversationMemory, user_id=current_user.id, skip=skip, limit=limit)
    return memories