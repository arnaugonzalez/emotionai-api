"""
Data Management Router

Handles legacy data endpoints for emotional records, breathing sessions, 
breathing patterns, and custom emotions. These endpoints maintain compatibility
with the existing Flutter application.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
import logging

from ....infrastructure.container import ApplicationContainer, get_container
from ....infrastructure.database.models import (
    EmotionalRecordModel, 
    BreathingSessionModel, 
    BreathingPatternModel,
    CustomEmotionModel,
    UserModel
)
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)


# Authentication dependency (temporary - will be moved to auth module later)
async def get_current_user_id(container: ApplicationContainer = Depends(get_container)) -> UUID:
    """Get current authenticated user ID - for now uses test user"""
    db = container.database
    
    async with db.get_session() as session:
        test_user = await session.execute(
            select(UserModel.id).where(UserModel.email == "test@emotionai.com")
        )
        user_id = test_user.scalar_one_or_none()
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated"
            )
        
        return user_id


# Exception handling utility
def handle_database_error(e: Exception, operation: str, entity: str) -> HTTPException:
    """Handle database errors with appropriate HTTP status codes"""
    logger.error(f"Database error during {operation} {entity}: {e}")
    
    # Handle specific database errors
    if "foreign key constraint" in str(e).lower():
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reference in {entity} data"
        )
    elif "unique constraint" in str(e).lower():
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{entity.title()} already exists"
        )
    elif "not null constraint" in str(e).lower():
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required fields in {entity} data"
        )
    else:
        return HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error {operation} {entity}"
        )




def validate_emotional_record(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate emotional record data"""
    try:
        # Handle None values safely
        color_value = data.get("color")
        intensity_value = data.get("intensity")
        
        return {
            "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
            "source": str(data.get("source", "manual")),
            "description": str(data.get("description", "")),
            "emotion": str(data.get("emotion", "neutral")),
            "color": int(color_value) if color_value is not None else 7829367,
            "custom_emotion_name": data.get("custom_emotion_name"),
            "custom_emotion_color": data.get("custom_emotion_color"),
            "created_at": str(data.get("created_at", datetime.now().isoformat())),
            "intensity": max(1, min(10, int(intensity_value) if intensity_value is not None else 5)),
        }
    except Exception as e:
        logger.error(f"Error validating emotional record: {e}")
        raise


def validate_breathing_session(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate breathing session data"""
    try:
        return {
            "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
            "pattern": str(data.get("pattern", "Basic Breathing")),
            "rating": max(1.0, min(5.0, float(data.get("rating", 3.0)))),
            "comment": data.get("comment"),
            "created_at": str(data.get("created_at", datetime.now().isoformat())),
        }
    except Exception as e:
        logger.error(f"Error validating breathing session: {e}")
        raise


def validate_breathing_pattern(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate breathing pattern data"""
    try:
        return {
            "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
            "name": str(data.get("name", "Unnamed Pattern")),
            "inhale_seconds": max(1, min(30, int(data.get("inhale_seconds") or 4))),
            "hold_seconds": max(0, min(30, int(data.get("hold_seconds") or 4))),
            "exhale_seconds": max(1, min(30, int(data.get("exhale_seconds") or 4))),
            "cycles": max(1, min(20, int(data.get("cycles") or 4))),
            "rest_seconds": max(0, min(10, int(data.get("rest_seconds") or 0))),
        }
    except Exception as e:
        logger.error(f"Error validating breathing pattern: {e}")
        raise


def validate_custom_emotion(data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate custom emotion data"""
    try:
        color_value = data.get("color")
        return {
            "id": str(data.get("id", f"default_{int(datetime.now().timestamp())}")),
            "name": str(data.get("name", "Custom Emotion")),
            "color": int(color_value) if color_value is not None else 7829367,
            "created_at": str(data.get("created_at", datetime.now().isoformat())),
        }
    except Exception as e:
        logger.error(f"Error validating custom emotion: {e}")
        raise


# Emotional Records Endpoints
@router.get("/emotional_records/")
async def get_emotional_records(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)):
    """Get all emotional records from database with validation"""
    
    try:
        # Get database connection
        db = container.database
        
        async with db.get_session() as session:
            
            # Get all emotional records for the user
            emotional_records_result = await session.execute(
                select(EmotionalRecordModel)
                .where(EmotionalRecordModel.user_id == user_id)
                .order_by(EmotionalRecordModel.recorded_at.desc())
            )
            emotional_records = emotional_records_result.scalars().all()
            
            # Convert to Flutter-compatible format
            records_data = []
            for er in emotional_records:
                # Extract color from context_data if available
                color = None
                custom_emotion_name = None
                custom_emotion_color = None
                source = "database"
                
                if er.context_data:
                    color = er.context_data.get("color")
                    custom_emotion_name = er.context_data.get("custom_emotion_name")
                    custom_emotion_color = er.context_data.get("custom_emotion_color")
                    source = er.context_data.get("source", "database")
                
                record_dict = {
                    "id": str(er.id),
                    "source": source,
                    "emotion": er.emotion,
                    "intensity": er.intensity,
                    "description": er.notes or "",
                    "created_at": er.recorded_at.isoformat(),
                    "color": color,
                    "custom_emotion_name": custom_emotion_name,
                    "custom_emotion_color": custom_emotion_color
                }
                records_data.append(record_dict)
            
            # Apply validation to ensure consistent data types
            validated_records = [validate_emotional_record(record) for record in records_data]
            logger.info(f"✅ Returning {len(validated_records)} validated emotional records from database")
            return validated_records
    
    except Exception as e:
        raise handle_database_error(e, "retrieving", "emotional records")


@router.post("/emotional_records/")
async def create_emotional_record(
    record: dict,
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)):
    """Create a new emotional record and save to database"""
    
    try:
        logger.info(f"📥 Received emotional record data: {record}")
        
        # Get database connection
        db = container.database
        
        async with db.get_session() as session:
            
            # Create the emotional record model
            emotional_record = EmotionalRecordModel(
                id=uuid4(),
                user_id=user_id,
                emotion=record.get("emotion", "neutral"),
                intensity=max(1, min(10, int(record.get("intensity") or 5))),
                triggers=record.get("triggers", []),
                notes=record.get("description", ""),
                context_data={
                    "source": record.get("source", "flutter_app"),
                    "color": record.get("color"),
                    "custom_emotion_name": record.get("custom_emotion_name"),
                    "custom_emotion_color": record.get("custom_emotion_color"),
                },
                tags=[],  # Will be processed later by AI
                tag_confidence=None,
                processed_for_tags=False,
                recorded_at=datetime.now()
            )
            
            # Save to database
            session.add(emotional_record)
            await session.commit()
            
            logger.info(f"✅ Successfully saved emotional record to database with ID: {emotional_record.id}")
            
            # Return Flutter-compatible response
            response = {
                "id": str(emotional_record.id),
                "emotion": emotional_record.emotion,
                "intensity": emotional_record.intensity,
                "description": emotional_record.notes,
                "created_at": emotional_record.recorded_at.isoformat(),
                "source": "database",
                "status": "saved"
            }
            
            logger.info(f"📤 Returning response: {response}")
            return response
    
    except Exception as e:
        raise handle_database_error(e, "creating", "emotional record"
        )


# Breathing Sessions Endpoints
@router.get("/breathing_sessions/")
async def get_breathing_sessions(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)):
    """Get all breathing sessions from database with validation"""
    
    try:
        # Get database connection
        db = container.database
        
        async with db.get_session() as session:
            
            # Get all breathing sessions for the user
            breathing_sessions_result = await session.execute(
                select(BreathingSessionModel)
                .where(BreathingSessionModel.user_id == user_id)
                .order_by(BreathingSessionModel.created_at.desc())
            )
            breathing_sessions = breathing_sessions_result.scalars().all()
            
            # Convert to Flutter-compatible format
            sessions_data = []
            for bs in breathing_sessions:
                session_dict = {
                    "id": str(bs.id),
                    "pattern": bs.pattern_name,
                    "rating": float(bs.effectiveness_rating or 3.0),
                    "comment": bs.notes or "",
                    "created_at": bs.created_at.isoformat()
                }
                sessions_data.append(session_dict)
        
        # Apply validation to ensure consistent data types
            validated_sessions = [validate_breathing_session(s) for s in sessions_data]
            logger.info(f"Returning {len(validated_sessions)} breathing sessions from database")
        return validated_sessions
    
    except Exception as e:
        raise handle_database_error(e, "retrieving", "breathing sessions")


@router.post("/breathing_sessions/")
async def create_breathing_session(
    session: dict,
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)):
    """Create a new breathing session and save to database"""
    
    try:
        logger.info(f"📥 Received breathing session data: {session}")
        
        # Get database connection
        db = container.database
        
        async with db.get_session() as db_session:
            
            # Create the breathing session model
            breathing_session = BreathingSessionModel(
                id=uuid4(),
                user_id=user_id,
                pattern_name=session.get("pattern", "Basic Breathing"),
                duration_minutes=session.get("duration_minutes", 5),
                completed=session.get("completed", True),
                effectiveness_rating=max(1, min(5, int(float(session.get("rating") or 3.0)))),
                notes=session.get("comment"),
                session_data={
                    "source": "flutter_app",
                    "original_data": session
                },
                tags=[],  # Will be processed later by AI
                tag_confidence=None,
                processed_for_tags=False,
                started_at=datetime.now(),
                completed_at=datetime.now() if session.get("completed", True) else None
            )
            
            # Save to database
            db_session.add(breathing_session)
            await db_session.commit()
            
            logger.info(f"✅ Successfully saved breathing session to database with ID: {breathing_session.id}")
            
            # Return Flutter-compatible response
            response = {
                "id": str(breathing_session.id),
                "pattern": breathing_session.pattern_name,
                "rating": float(breathing_session.effectiveness_rating or 3.0),
                "comment": breathing_session.notes or "",
                "created_at": breathing_session.created_at.isoformat(),
                "status": "saved"
            }
            
            logger.info(f"📤 Returning breathing session response: {response}")
            return response
    
    except Exception as e:
        raise handle_database_error(e, "creating", "breathing session"
        )


# Breathing Patterns Endpoints
@router.get("/breathing_patterns/")
async def get_breathing_patterns(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)):
    """Get all breathing patterns from database (presets + user patterns)"""
    
    try:
        # Get database connection
        db = container.database
        
        async with db.get_session() as session:
            
            # Get preset patterns (global patterns)
            preset_patterns_result = await session.execute(
                select(BreathingPatternModel)
                .where(BreathingPatternModel.is_preset == True)
                .where(BreathingPatternModel.is_active == True)
                .order_by(BreathingPatternModel.name)
            )
            preset_patterns = preset_patterns_result.scalars().all()
            
            # Get user-specific patterns for the user
            user_patterns = []
            if user_id:
                user_patterns_result = await session.execute(
                    select(BreathingPatternModel)
                    .where(BreathingPatternModel.user_id == user_id)
                    .where(BreathingPatternModel.is_active == True)
                    .order_by(BreathingPatternModel.name)
                )
                user_patterns = user_patterns_result.scalars().all()
            
            # Combine and convert to Flutter-compatible format
            all_patterns = list(preset_patterns) + list(user_patterns)
            patterns_data = []
            for pattern in all_patterns:
                pattern_dict = {
                    "id": str(pattern.id),
                    "name": pattern.name,
                    "inhale_seconds": pattern.inhale_seconds,
                    "hold_seconds": pattern.hold_seconds,
                    "exhale_seconds": pattern.exhale_seconds,
                    "cycles": pattern.cycles,
                    "rest_seconds": pattern.rest_seconds
                }
                patterns_data.append(pattern_dict)
            
            # If no patterns exist, create some default presets
            if not patterns_data:
                logger.info("No patterns found, returning default presets")
                patterns_data = [
                    {
                        "id": "preset_1",
                "name": "4-7-8 Breathing",
                "inhale_seconds": 4,
                "hold_seconds": 7,
                "exhale_seconds": 8,
                "cycles": 4,
                "rest_seconds": 0
            },
            {
                        "id": "preset_2",
                "name": "Box Breathing",
                "inhale_seconds": 4,
                "hold_seconds": 4,
                "exhale_seconds": 4,
                "cycles": 6,
                "rest_seconds": 0
            }
        ]
        
        # Apply validation to ensure consistent data types
            validated_patterns = [validate_breathing_pattern(pattern) for pattern in patterns_data]
            logger.info(f"Returning {len(validated_patterns)} breathing patterns from database")
        return validated_patterns
    
    except Exception as e:
        raise handle_database_error(e, "retrieving", "breathing patterns")


@router.post("/breathing_patterns/")
async def create_breathing_pattern(
    pattern: dict,
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)):
    """Create a new breathing pattern and save to database"""
    
    try:
        logger.info(f"📥 Received breathing pattern data: {pattern}")
        
        # Get database connection
        db = container.database
        
        async with db.get_session() as db_session:
            
            # Create the breathing pattern model
            breathing_pattern = BreathingPatternModel(
                id=uuid4(),
                user_id=user_id,
                name=pattern.get("name", "Custom Pattern"),
                inhale_seconds=max(1, min(30, int(pattern.get("inhale_seconds") or 4))),
                hold_seconds=max(0, min(30, int(pattern.get("hold_seconds") or 0))),
                exhale_seconds=max(1, min(30, int(pattern.get("exhale_seconds") or 4))),
                cycles=max(1, min(20, int(pattern.get("cycles") or 4))),
                rest_seconds=max(0, min(10, int(pattern.get("rest_seconds") or 0))),
                description=pattern.get("description"),
                is_preset=False,  # User-created patterns are not presets
                is_active=True,
                tags=[],  # Will be processed later by AI
                tag_confidence=None,
                processed_for_tags=False
            )
            
            # Save to database
            db_session.add(breathing_pattern)
            await db_session.commit()
            
            logger.info(f"✅ Successfully saved breathing pattern to database with ID: {breathing_pattern.id}")
            
            # Return Flutter-compatible response
            response = {
                "id": str(breathing_pattern.id),
                "name": breathing_pattern.name,
                "inhale_seconds": breathing_pattern.inhale_seconds,
                "hold_seconds": breathing_pattern.hold_seconds,
                "exhale_seconds": breathing_pattern.exhale_seconds,
                "cycles": breathing_pattern.cycles,
                "rest_seconds": breathing_pattern.rest_seconds,
                "status": "saved"
            }
            
            logger.info(f"📤 Returning breathing pattern response: {response}")
            return response
    
    except Exception as e:
        raise handle_database_error(e, "creating", "breathing pattern"
        )


# Custom Emotions Endpoints  
@router.get("/custom_emotions/")
async def get_custom_emotions(
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)):
    """Get all custom emotions from database with validation"""
    
    try:
        # Get database connection
        db = container.database
        
        async with db.get_session() as session:
            
            # Get all custom emotions for the user
            custom_emotions_result = await session.execute(
                select(CustomEmotionModel)
                .where(CustomEmotionModel.user_id == user_id)
                .where(CustomEmotionModel.is_active == True)
                .order_by(CustomEmotionModel.name)
            )
            custom_emotions = custom_emotions_result.scalars().all()
            
            # Convert to Flutter-compatible format
            emotions_data = []
            for emotion in custom_emotions:
                emotion_dict = {
                    "id": str(emotion.id),
                    "name": emotion.name,
                    "color": emotion.color,
                    "created_at": emotion.created_at.isoformat()
                }
                emotions_data.append(emotion_dict)
        
        # Apply validation to ensure consistent data types
            validated_emotions = [validate_custom_emotion(emotion) for emotion in emotions_data]
            logger.info(f"Returning {len(validated_emotions)} custom emotions from database")
        return validated_emotions
    
    except Exception as e:
        raise handle_database_error(e, "retrieving", "custom emotions")


@router.post("/custom_emotions/")
async def create_custom_emotion(
    emotion: dict,
    user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)):
    """Create a new custom emotion and save to database"""
    
    try:
        logger.info(f"📥 Received custom emotion data: {emotion}")
        
        # Get database connection
        db = container.database
        
        async with db.get_session() as db_session:
            
            # Check for duplicate emotion name for this user
            existing_emotion_result = await db_session.execute(
                select(CustomEmotionModel)
                .where(CustomEmotionModel.user_id == user_id)
                .where(CustomEmotionModel.name == emotion.get("name", ""))
                .where(CustomEmotionModel.is_active == True)
            )
            existing_emotion = existing_emotion_result.scalar_one_or_none()
            
            if existing_emotion:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Custom emotion '{emotion.get('name')}' already exists"
                )
            
            # Create the custom emotion model
            custom_emotion = CustomEmotionModel(
                id=uuid4(),
                user_id=user_id,
                name=emotion.get("name", "Custom Emotion"),
                color=int(emotion.get("color") or 7829367),  # Default color
                description=emotion.get("description"),
                is_active=True,
                usage_count=0,
                last_used_at=None,
                tags=[],  # Will be processed later by AI
                tag_confidence=None,
                processed_for_tags=False
            )
            
            # Save to database
            db_session.add(custom_emotion)
            await db_session.commit()
            
            logger.info(f"✅ Successfully saved custom emotion to database with ID: {custom_emotion.id}")
            
            # Return Flutter-compatible response
            response = {
                "id": str(custom_emotion.id),
                "name": custom_emotion.name,
                "color": custom_emotion.color,
                "created_at": custom_emotion.created_at.isoformat(),
                "status": "saved"
            }
            
            logger.info(f"📤 Returning custom emotion response: {response}")
            return response
    
    except HTTPException:
        # Re-raise HTTP exceptions (like duplicate name)
        raise
    except Exception as e:
        raise handle_database_error(e, "creating", "custom emotion"
        )


# Health check for data endpoints
@router.get("/data/health")
async def data_health_check():
    """Health check for data management endpoints"""
    return {
        "status": "healthy",
        "endpoints": [
            "emotional_records",
            "breathing_sessions", 
            "breathing_patterns",
            "custom_emotions"
        ],
        "message": "Data management endpoints are operational with validation",
        "timestamp": datetime.now().isoformat(),
        "validation": "enabled"
    } 