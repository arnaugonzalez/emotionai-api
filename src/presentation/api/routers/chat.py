"""
Chat Router

Handles agent conversations and related functionality.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel
from uuid import uuid4
from fastapi.security import HTTPBearer

from ....application.dtos.chat_dtos import (
    AgentStatusResponse, ConversationHistoryResponse
)
from ....application.chat.use_cases.agent_chat_use_case import AgentChatUseCase
from ....application.exceptions import ApplicationException
from ....infrastructure.container import ApplicationContainer
from .deps import get_container, get_current_user_id

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)


def get_container(request: Request) -> ApplicationContainer:
    # Provided by deps; keep for FastAPI signature clarity
    return request.app.state.container


class ChatApiRequest(BaseModel):
    agent_type: Optional[str] = "therapy"
    message: str
    context: Optional[Dict[str, Any]] = None


class ChatApiResponse(BaseModel):
    message: str
    agent_type: str
    conversation_id: Optional[str] = None
    suggestions: List[str] = []
    timestamp: str


@router.post("/chat", response_model=ChatApiResponse, summary="Send message to agent")
async def chat_with_agent(
    payload: ChatApiRequest,
    current_user_id: UUID = Depends(get_current_user_id),
    container: ApplicationContainer = Depends(get_container)
):
    """Send a message to an AI agent and get response"""
    
    logger.info(f"Chat request received - User: {current_user_id}, Agent: {payload.agent_type}, Message length: {len(payload.message)}")
    
    try:
        # Validate message length (limit to 700 chars from our side)
        if payload.message is None or len(payload.message) == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message is required")
        if len(payload.message) > 700:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message must be at most 700 characters")
        # Get the agent chat use case from container
        chat_use_case: AgentChatUseCase = container.agent_chat_use_case
        logger.info("Agent chat use case retrieved successfully")
        
        # Execute the use case
        logger.info("Executing agent chat use case...")
        response = await chat_use_case.execute(
            user_id=current_user_id,
            agent_type=payload.agent_type or "therapy",
            message=payload.message,
            context=payload.context or {}
        )
        logger.info(f"Use case executed successfully. Response type: {type(response)}")
        logger.info(f"Response content: {response}")
        
        # Log response details for debugging
        if isinstance(response, dict) and 'message' in response:
            logger.info(f"Response message length: {len(response['message'])}")
            logger.info(f"Response keys: {list(response.keys())}")
        elif hasattr(response, 'message'):
            logger.info(f"Response message length: {len(response.message)}")
        else:
            logger.warning(f"Response object missing 'message' attribute. Response: {response}")
        
        # Adapt domain response to API response schema expected by Flutter
        try:
            if isinstance(response, dict):
                # Handle dictionary response (fallback)
                if 'message' not in response:
                    raise ValueError("Response missing 'message' field")
                if 'agent_type' not in response:
                    raise ValueError("Response missing 'agent_type' field")
                
                api_response = ChatApiResponse(
                    message=response['message'],
                    agent_type=response['agent_type'],
                    conversation_id=(response.get('conversation_id') or f"conv_{uuid4()}"),
                    suggestions=[],
                    timestamp=(response.get('timestamp') or "")
                )
            elif hasattr(response, 'message') and hasattr(response, 'agent_type'):
                # Handle TherapyResponse object
                api_response = ChatApiResponse(
                    message=response.message,
                    agent_type=response.agent_type,
                    conversation_id=response.conversation_id,
                    suggestions=response.follow_up_suggestions if hasattr(response, 'follow_up_suggestions') else [],
                    timestamp=response.timestamp.isoformat() if response.timestamp else datetime.utcnow().isoformat()
                )
                
                # Log therapeutic approach for debugging
                if hasattr(response, 'therapeutic_approach'):
                    logger.info(f"Therapeutic approach: {response.therapeutic_approach}")
                if hasattr(response, 'crisis_detected') and response.crisis_detected:
                    logger.warning("Crisis detected in therapy response")
                    
            else:
                raise ValueError("Response object missing required attributes")
                
        except (KeyError, AttributeError, ValueError) as e:
            logger.error(f"Error creating API response: {e}. Response: {response}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "InvalidResponseFormat",
                    "message": f"Invalid response format from agent service: {str(e)}",
                    "details": {
                        "response_type": type(response).__name__,
                        "response_content": str(response)
                    }
                }
            )
        
        logger.info("API response created successfully")
        return api_response
        
    except ApplicationException as e:
        logger.error(f"Application exception in chat: {e.__class__.__name__}: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": e.__class__.__name__,
                "message": e.message,
                "details": e.details
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"An unexpected error occurred while processing your request: {str(e)}",
                "details": {
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                }
            }
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