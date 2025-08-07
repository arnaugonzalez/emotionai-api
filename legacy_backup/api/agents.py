from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import logging

from app.dependencies import get_db, get_current_user
from services.agent_manager import AgentManager
from app.models import User
from models.responses import AgentResponse, ChatMessage, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])

# Request/Response Models
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    agent_type: str = Field(default="therapy", pattern="^(therapy|wellness)$")
    context: Optional[Dict[str, Any]] = None

class AgentStatusResponse(BaseModel):
    active: bool
    agent_type: str
    last_interaction: Optional[str] = None
    memory_summary: Optional[str] = None
    personality: str
    conversation_length: int = 0

class EmotionalRecordRequest(BaseModel):
    emotion_type: str
    intensity: int = Field(ge=1, le=10)
    context: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

class BreathingSessionRequest(BaseModel):
    pattern_name: str
    duration_seconds: int
    session_data: Optional[Dict[str, Any]] = None

# Dependency injection for AgentManager
def get_agent_manager() -> AgentManager:
    # This will be injected from the main app
    from app.main import agent_manager
    if agent_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent manager not initialized"
        )
    return agent_manager

@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Send a message to user's personalized agent"""
    try:
        # Process message with agent
        response = await agent_manager.process_message(
            user_id=current_user.id,
            message=request.message,
            agent_type=request.agent_type,
            context=request.context,
            db_session=db
        )
        
        if response is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agent service temporarily unavailable"
            )
        
        # Return response
        return ChatResponse(
            message=response,
            agent_type=request.agent_type,
            user_message=request.message
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )

@router.get("/status", response_model=AgentStatusResponse)
async def get_agent_status(
    agent_type: str = "therapy",
    current_user: User = Depends(get_current_user),
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Get status of user's agent"""
    try:
        status_data = await agent_manager.get_agent_status(
            user_id=current_user.id,
            agent_type=agent_type
        )
        
        return AgentStatusResponse(
            agent_type=agent_type,
            **status_data
        )
        
    except Exception as e:
        logger.error(f"Error getting agent status for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent status"
        )

@router.post("/clear-memory")
async def clear_agent_memory(
    agent_type: str = "therapy",
    current_user: User = Depends(get_current_user),
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Clear agent's conversation memory"""
    try:
        success = await agent_manager.clear_agent_memory(
            user_id=current_user.id,
            agent_type=agent_type
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found or already inactive"
            )
        
        return {"message": "Agent memory cleared successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing agent memory for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear agent memory"
        )

@router.post("/emotional-record")
async def add_emotional_record(
    request: EmotionalRecordRequest,
    agent_type: str = "therapy",
    current_user: User = Depends(get_current_user),
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Add emotional record to agent's understanding"""
    try:
        emotion_data = {
            'emotion_type': request.emotion_type,
            'intensity': request.intensity,
            'context': request.context,
            'location': request.location,
            'notes': request.notes
        }
        
        success = await agent_manager.add_emotional_record(
            user_id=current_user.id,
            emotion_data=emotion_data,
            agent_type=agent_type
        )
        
        return {
            "message": "Emotional record added successfully" if success 
                      else "Agent not active, record will be available on next interaction"
        }
        
    except Exception as e:
        logger.error(f"Error adding emotional record for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add emotional record"
        )

@router.post("/breathing-session")
async def add_breathing_session(
    request: BreathingSessionRequest,
    agent_type: str = "therapy",
    current_user: User = Depends(get_current_user),
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Add breathing session to agent's understanding"""
    try:
        session_data = {
            'pattern_name': request.pattern_name,
            'duration_seconds': request.duration_seconds,
            'session_data': request.session_data or {}
        }
        
        success = await agent_manager.add_breathing_session(
            user_id=current_user.id,
            session_data=session_data,
            agent_type=agent_type
        )
        
        return {
            "message": "Breathing session added successfully" if success 
                      else "Agent not active, session will be available on next interaction"
        }
        
    except Exception as e:
        logger.error(f"Error adding breathing session for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add breathing session"
        )

@router.put("/context")
async def update_agent_context(
    context: Dict[str, Any],
    agent_type: str = "therapy",
    current_user: User = Depends(get_current_user),
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Update agent context with new information"""
    try:
        success = await agent_manager.update_agent_context(
            user_id=current_user.id,
            context_data=context,
            agent_type=agent_type
        )
        
        return {
            "message": "Agent context updated successfully" if success 
                      else "Agent not active, context will be available on next interaction"
        }
        
    except Exception as e:
        logger.error(f"Error updating agent context for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent context"
        )

@router.get("/admin/stats")
async def get_agent_stats(
    current_user: User = Depends(get_current_user),
    agent_manager: AgentManager = Depends(get_agent_manager)
):
    """Get agent statistics (admin only)"""
    # Add admin check if needed
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        stats = agent_manager.get_active_agent_count()
        return {
            "active_agents": stats,
            "total_active_users": len(agent_manager.active_agents)
        }
        
    except Exception as e:
        logger.error(f"Error getting agent stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent statistics"
        ) 