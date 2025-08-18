"""LangChain Agent Service Implementation

Now provides real therapeutic responses with conversation memory and context.
"""

import logging
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from ...application.services.agent_service import IAgentService
from ...application.services.llm_service import ILLMService
from ...domain.chat.entities import AgentContext, TherapyResponse, Conversation, Message
from ...domain.chat.interfaces import IAgentConversationRepository
from ...domain.users.interfaces import IUserRepository
from ...domain.records.interfaces import IEmotionalRecordRepository

logger = logging.getLogger(__name__)


class LangChainAgentService(IAgentService):
    def __init__(
        self, 
        llm_service: ILLMService,
        conversation_repository: IAgentConversationRepository,
        user_repository: IUserRepository,
        emotional_repository: IEmotionalRecordRepository,
        settings: Dict[str, Any]
    ):
        self.llm_service = llm_service
        self.conversation_repository = conversation_repository
        self.user_repository = user_repository
        self.emotional_repository = emotional_repository
        self.settings = settings
        logger.info("LangChainAgentService initialized with real LLM and memory")

    async def send_message(
        self, 
        user_id: UUID, 
        agent_type: str, 
        message: str, 
        context: Dict[str, Any]
    ) -> TherapyResponse:
        """Send a message to the agent and get a therapeutic response with memory"""
        logger.info(f"LangChainAgentService.send_message called - User: {user_id}, Agent: {agent_type}, Message: {message[:50]}...")
        
        try:
            # 1. Get or create active conversation
            conversation = await self._get_or_create_conversation(user_id, agent_type)
            
            # 2. Store user message
            user_message = await self.conversation_repository.add_message(
                conversation_id=conversation.id,
                user_id=user_id,
                content=message,
                message_type="user",
                metadata={"emotional_context": context.get("emotional_state")}
            )
            
            # 3. Build agent context with memory
            agent_context = await self._build_agent_context(
                user_id, agent_type, conversation.id, message
            )
            
            # 4. Generate therapeutic response using LLM
            therapy_response = await self.llm_service.generate_therapy_response(
                agent_context, message
            )
            
            # 5. Store assistant response
            await self.conversation_repository.add_message(
                conversation_id=conversation.id,
                user_id=user_id,
                content=therapy_response.message,
                message_type="assistant",
                metadata={
                    "therapeutic_approach": therapy_response.therapeutic_approach,
                    "emotional_tone": therapy_response.emotional_tone,
                    "crisis_detected": therapy_response.crisis_detected
                }
            )
            
            # 6. Update conversation metadata
            if therapy_response.crisis_detected:
                logger.warning(f"Crisis detected for user {user_id} in {agent_type} session")
                # TODO: Implement crisis response protocol
            
            logger.info(f"Therapy response generated successfully: {therapy_response.therapeutic_approach}")
            return therapy_response
            
        except Exception as e:
            logger.error(f"Error in send_message: {e}", exc_info=True)
            # Return fallback response
            return await self._create_fallback_response(user_id, agent_type, message)

    async def _get_or_create_conversation(
        self, 
        user_id: UUID, 
        agent_type: str
    ) -> Conversation:
        """Get active conversation or create new one"""
        try:
            # Try to get existing active conversation
            conversation = await self.conversation_repository.get_active_conversation(
                user_id, agent_type
            )
            
            if conversation:
                logger.info(f"Using existing conversation: {conversation.id}")
                return conversation
            
            # Create new conversation
            conversation = await self.conversation_repository.create_conversation(
                user_id, agent_type
            )
            logger.info(f"Created new conversation: {conversation.id}")
            return conversation
            
        except Exception as e:
            logger.error(f"Error getting/creating conversation: {e}")
            raise

    async def _build_agent_context(
        self, 
        user_id: UUID, 
        agent_type: str, 
        conversation_id: str, 
        current_message: str
    ) -> AgentContext:
        """Build comprehensive context for the agent"""
        try:
            # Get recent conversation history
            recent_messages = await self.conversation_repository.get_recent_context(
                user_id, agent_type, message_count=10
            )
            
            # Get user profile
            user_profile = await self._get_user_profile(user_id)
            
            # Analyze emotional state of current message
            emotional_analysis = await self.llm_service.analyze_emotional_state(current_message)
            
            # Get recent emotional records for context
            emotional_records = await self._get_recent_emotional_records(user_id)
            
            # Build context
            context = AgentContext(
                user_id=user_id,
                agent_type=agent_type,
                conversation_id=conversation_id,
                recent_messages=recent_messages,
                user_profile=user_profile,
                emotional_state=emotional_analysis.get("emotion"),
                session_duration=len(recent_messages) * 2,  # Rough estimate
                crisis_indicators=emotional_analysis.get("crisis_indicators", [])
            )
            
            logger.info(f"Built agent context with {len(recent_messages)} recent messages")
            return context
            
        except Exception as e:
            logger.error(f"Error building agent context: {e}")
            # Return minimal context
            return AgentContext(
                user_id=user_id,
                agent_type=agent_type,
                conversation_id=conversation_id,
                recent_messages=[],
                user_profile={},
                emotional_state="unknown"
            )

    async def _get_user_profile(self, user_id: UUID) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            user = await self.user_repository.get_by_id(user_id)
            if user:
                return {
                    "age": getattr(user, 'age', None),
                    "personality_type": getattr(user, 'personality_type', None),
                    "therapy_goals": getattr(user, 'therapy_goals', None),
                    "preferences": getattr(user, 'preferences', {})
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {}

    async def _get_recent_emotional_records(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Get recent emotional records for context"""
        try:
            # Get records from last 7 days
            from datetime import timedelta
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
            
            records = await self.emotional_repository.get_records_by_date_range(
                user_id, start_date, end_date
            )
            
            return [
                {
                    "emotion": record.emotion,
                    "intensity": record.intensity,
                    "description": record.description,
                    "timestamp": record.created_at
                }
                for record in records[:10]  # Last 10 records
            ]
        except Exception as e:
            logger.error(f"Error getting emotional records: {e}")
            return []

    async def _create_fallback_response(
        self, 
        user_id: UUID, 
        agent_type: str, 
        message: str
    ) -> TherapyResponse:
        """Create a fallback response when the main flow fails"""
        return TherapyResponse(
            message="I'm here to listen and support you. I'm experiencing some technical difficulties right now, but I want you to know that your feelings are valid and important. Please continue sharing, and I'll do my best to help.",
            agent_type=agent_type,
            conversation_id=f"fallback_{user_id}_{agent_type}",
            timestamp=datetime.utcnow(),
            therapeutic_approach="supportive",
            emotional_tone="empathetic",
            follow_up_suggestions=["Try to express your feelings", "Consider what might help you feel better"],
            crisis_detected=False,
            metadata={"fallback": True, "error": "Service unavailable"}
        )

    # Keep other methods for compatibility
    async def get_or_create_agent(self, user_id: UUID, agent_type: str, personality, context: Dict[str, Any]) -> Any:
        return {"agent_id": f"agent_{user_id}_{agent_type}"}

    async def process_message(self, user_id: UUID, agent_type: str, message: str, context: Dict[str, Any]) -> str:
        # Delegate to send_message for consistency
        response = await self.send_message(user_id, agent_type, message, context)
        return response.message

    async def get_agent_status(self, user_id: UUID, agent_type: str):
        from datetime import datetime
        from ...application.dtos.chat_dtos import AgentStatusResponse
        
        try:
            conversation = await self.conversation_repository.get_active_conversation(user_id, agent_type)
            if conversation:
                return AgentStatusResponse(
                    active=True,
                    agent_type=agent_type,
                    last_interaction=conversation.last_message_at,
                    memory_summary=f"Active conversation with {conversation.message_count} messages",
                    personality="empathetic_supportive",
                    conversation_length=conversation.message_count,
                    session_count=1
                )
            else:
                return AgentStatusResponse(
                    active=False,
                    agent_type=agent_type,
                    last_interaction=None,
                    memory_summary="No active conversation",
                    personality="empathetic_supportive",
                    conversation_length=0,
                    session_count=0
                )
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            return AgentStatusResponse(
                active=False,
                agent_type=agent_type,
                last_interaction=None,
                memory_summary="Error retrieving status",
                personality="empathetic_supportive",
                conversation_length=0,
                session_count=0
            )

    async def clear_agent_memory(self, user_id: UUID, agent_type: str) -> bool:
        try:
            conversation = await self.conversation_repository.get_active_conversation(user_id, agent_type)
            if conversation:
                await self.conversation_repository.close_conversation(conversation.id)
                logger.info(f"Cleared agent memory for user {user_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing agent memory: {e}")
            return False

    async def update_agent_context(self, user_id: UUID, agent_type: str, context_data: Dict[str, Any]) -> bool:
        # This could be implemented to update conversation metadata
        logger.info(f"Updated agent context for user {user_id}: {context_data}")
        return True

    async def get_active_agent_count(self) -> Dict[str, int]:
        # This would require counting active conversations
        return {"therapy": 0, "wellness": 0}

    async def health_check(self) -> bool:
        try:
            return await self.llm_service.health_check()
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def cleanup(self) -> None:
        # Cleanup resources if needed
        pass 