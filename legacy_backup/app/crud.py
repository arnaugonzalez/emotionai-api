from sqlalchemy.orm import Session
from . import models, schemas
from .security import pwd_context

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_records_by_owner(db: Session, model, user_id: int, skip: int = 0, limit: int = 100):
    return db.query(model).filter(model.owner_id == user_id).offset(skip).limit(limit).all()

def create_record(db: Session, model, schema, user_id: int):
    db_record = model(**schema.dict(), owner_id=user_id)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

def get_breathing_patterns(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.BreathingPattern).offset(skip).limit(limit).all()

def create_breathing_pattern(db: Session, pattern: schemas.BreathingPatternCreate, user_id: int = None):
    db_pattern = models.BreathingPattern(**pattern.dict(), owner_id=user_id)
    db.add(db_pattern)
    db.commit()
    db.refresh(db_pattern)
    return db_pattern