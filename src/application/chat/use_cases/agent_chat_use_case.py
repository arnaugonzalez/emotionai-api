import logging
from typing import Dict, Any, Optional
from uuid import UUID

from ....domain.users.interfaces import IUserRepository
from ....domain.events.interfaces import IEventRepository
from ....domain.records.interfaces import IEmotionalRecordRepository
from ....domain.breathing.interfaces import IBreathingSessionRepository
from ....domain.chat.interfaces import IAgentConversationRepository
from ....application.services.agent_service import IAgentService
from ....application.services.tagging_service import ITaggingService
from ....application.services.user_knowledge_service import IUserKnowledgeService
from ....application.services.similarity_search_service import ISimilaritySearchService

logger = logging.getLogger(__name__)


class AgentChatUseCase:
    def __init__(
        self,
        user_repository: IUserRepository,
        emotional_repository: IEmotionalRecordRepository,
        breathing_repository: IBreathingSessionRepository,
        conversation_repository: IAgentConversationRepository,
        event_repository: IEventRepository,
        agent_service: IAgentService,
        tagging_service: ITaggingService,
        user_knowledge_service: IUserKnowledgeService,
        similarity_search_service: ISimilaritySearchService,
    ) -> None:
        self.user_repository = user_repository
        self.emotional_repository = emotional_repository
        self.breathing_repository = breathing_repository
        self.conversation_repository = conversation_repository
        self.event_repository = event_repository
        self.agent_service = agent_service
        self.tagging_service = tagging_service
        self.user_knowledge_service = user_knowledge_service
        self.similarity_search_service = similarity_search_service

    async def execute(
        self,
        user_id: UUID,
        agent_type: str,
        message: str,
    context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        logger.info(f"AgentChatUseCase.execute called - User: {user_id}, Agent: {agent_type}, Message: {message[:50]}...")
        
        try:
            # Log the agent service type for debugging
            logger.info(f"Agent service type: {type(self.agent_service)}")
            
            # Check if agent service has the required method
            if not hasattr(self.agent_service, 'send_message'):
                logger.error(f"Agent service missing 'send_message' method. Available methods: {dir(self.agent_service)}")
                raise AttributeError("Agent service missing 'send_message' method")
            
            # Execute the use case
            logger.info("Calling agent_service.send_message...")
            response = await self.agent_service.send_message(user_id, agent_type, message, context or {})
            # Best-effort token usage logging if metadata is present
            try:
                usage = None
                model = None
                if hasattr(response, 'metadata') and isinstance(response.metadata, dict):
                    model = response.metadata.get('llm_model')
                    usage = response.metadata.get('usage') or response.metadata.get('token_usage')
                if isinstance(usage, dict):
                    token_total = int(usage.get('tokens_total') or 0)
                    token_prompt = int(usage.get('tokens_prompt') or 0)
                    token_completion = int(usage.get('tokens_completion') or 0)
                    if token_total > 0:
                        await self.tagging_service.token_usage_repo.log_usage(  # type: ignore[attr-defined]
                            user_id=user_id,
                            interaction_type='chat',
                            total_tokens=token_total,
                            tokens_prompt=token_prompt,
                            tokens_completion=token_completion,
                            model=model,
                            data_id=str(getattr(response, 'conversation_id', '') or ''),
                            metadata={'agent_type': agent_type}
                        )
            except Exception:
                # Don't fail the chat on logging problems
                logger.debug("Token usage logging skipped due to error", exc_info=True)
            logger.info(f"Agent service response received: {type(response)}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error in AgentChatUseCase.execute: {str(e)}", exc_info=True)
            raise


