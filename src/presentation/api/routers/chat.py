"""
Chat Router

Handles agent conversations and related functionality.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer

from ....application.dtos.chat_dtos import (
    ChatRequest, ChatResponse, AgentStatusResponse, ConversationHistoryResponse
)
from ....application.use_cases.agent_chat_use_case import AgentChatUseCase
from ....application.exceptions import ApplicationException
from ....infrastructure.container import ApplicationContainer

router = APIRouter()
security = HTTPBearer()


def get_container(request: Request) -> ApplicationContainer:
    """Get dependency injection container from app state"""
    return request.app.state.container


async def get_current_user_id(token: str = Depends(security)) -> UUID:
    """Extract user ID from JWT token"""
    # TODO: Implement JWT token validation and user ID extraction
    # For now, return a placeholder UUID
    return UUID("550e8400-e29b-41d4-a716-446655440000")


@router.post("/chat", response_model=ChatResponse, summary="Send message to agent")
async def chat_with_agent(
    request: ChatRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    """Send a message to an AI agent and get response"""
    
    try:
        # Get the agent chat use case from container
        chat_use_case: AgentChatUseCase = container.agent_chat_use_case
        
        # Execute the use case
        response = await chat_use_case.execute(
            user_id=current_user_id,
            agent_type=request.agent_type,
            message=request.message,
            context=request.context or {}
        )
        
        return response
        
    except ApplicationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.__class__.__name__,
                "message": e.message,
                "details": e.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request"
        )


@router.get("/agents/{agent_type}/status", response_model=AgentStatusResponse, summary="Get agent status")
async def get_agent_status(
    agent_type: str,
    current_user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    """Get the status of a specific agent for the current user"""
    
    try:
        agent_service = container.agent_service
        status_response = await agent_service.get_agent_status(
            user_id=current_user_id,
            agent_type=agent_type
        )
        
        return status_response
        
    except ApplicationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.__class__.__name__,
                "message": e.message
            }
        )


@router.delete("/agents/{agent_type}/memory", summary="Clear agent memory")
async def clear_agent_memory(
    agent_type: str,
    current_user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    """Clear the conversation memory for a specific agent"""
    
    try:
        agent_service = container.agent_service
        success = await agent_service.clear_agent_memory(
            user_id=current_user_id,
            agent_type=agent_type
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to clear agent memory"
            )
        
        return {"message": f"Successfully cleared memory for {agent_type} agent"}
        
    except ApplicationException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.__class__.__name__,
                "message": e.message
            }
        )


@router.get("/conversations", response_model=List[ConversationHistoryResponse], summary="Get conversation history")
async def get_conversation_history(
    agent_type: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    """Get conversation history for the current user"""
    
    try:
        # TODO: Implement conversation history retrieval
        # This would typically involve a conversation repository
        
        # Placeholder response
        return [
            {
                "id": "conv_123",
                "agent_type": agent_type or "therapy",
                "title": "Sample Conversation",
                "created_at": "2024-01-01T00:00:00Z",
                "last_message_at": "2024-01-01T01:00:00Z",
                "message_count": 10,
                "is_active": True
            }
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversation history"
        )


@router.get("/agents", summary="List available agents")
async def list_available_agents():
    """Get list of available agent types and their descriptions"""
    
    return {
        "agents": [
            {
                "type": "therapy",
                "name": "Therapy Agent",
                "description": "Provides therapeutic conversations and emotional support",
                "capabilities": ["emotional_support", "coping_strategies", "intelligent_tagging"]
            },
            {
                "type": "wellness",
                "name": "Wellness Agent", 
                "description": "Focuses on mindfulness, breathing exercises, and general wellness",
                "capabilities": ["mindfulness", "breathing_exercises", "wellness_tips"]
            }
        ]
    } 