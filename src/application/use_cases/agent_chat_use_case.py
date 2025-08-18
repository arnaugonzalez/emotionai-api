"""
Use Case: Agent Chat

Orchestrates the intelligent agent chat functionality with personalization,
tag-based context building, and user knowledge management.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID

from ...domain.users.interfaces import IUserRepository
from ...domain.records.interfaces import IEmotionalRecordRepository
from ...domain.breathing.interfaces import IBreathingSessionRepository
from ...domain.chat.interfaces import IAgentConversationRepository
from ...domain.events.interfaces import IEventRepository
from ...domain.entities.user import User
from ...domain.events.domain_events import AgentConversationStartedEvent, UserDataTaggedEvent
from ..services.agent_service import IAgentService
from ..services.tagging_service import ITaggingService, TagExtractionResult
from ..services.user_knowledge_service import IUserKnowledgeService
from ..services.similarity_search_service import ISimilaritySearchService
from ..dtos.chat_dtos import ChatRequest, ChatResponse
from ..exceptions import UserNotFoundException, AgentServiceException, TaggingServiceException


@dataclass
class AgentChatUseCase:
    """Use case for handling intelligent agent chat interactions with tagging"""
    
    user_repository: IUserRepository
    emotional_repository: IEmotionalRecordRepository
    breathing_repository: IBreathingSessionRepository
    conversation_repository: IAgentConversationRepository
    event_repository: IEventRepository
    agent_service: IAgentService
    tagging_service: ITaggingService
    user_knowledge_service: IUserKnowledgeService
    similarity_search_service: ISimilaritySearchService
    
    async def execute(self, request: ChatRequest) -> ChatResponse:
        """Execute the intelligent agent chat use case with tagging"""
        
        # 1. Get user and validate
        user = await self._get_and_validate_user(request.user_id)
        
        # 2. Extract semantic tags from user message
        user_context = await self.user_knowledge_service.get_personalization_context(
            user.id, "tagging"
        )
        
        try:
            tag_result = await self.tagging_service.extract_tags_from_message(
                content=request.message,
                user_context=user_context
            )
        except Exception as e:
            raise TaggingServiceException(f"Failed to extract tags: {str(e)}")
        
        # 3. Build intelligent personalized context using tags and knowledge
        context = await self._build_intelligent_context(user, request, tag_result)
        
        # 4. Get or create agent with enhanced context
        agent = await self.agent_service.get_or_create_agent(
            user_id=user.id,
            agent_type=request.agent_type,
            personality=user.agent_personality,
            context=context
        )
        
        # 5. Process message with agent using intelligent context
        try:
            response_message = await agent.process_message(request.message, context)
        except Exception as e:
            raise AgentServiceException(f"Agent processing failed: {str(e)}")
        
        # 6. Save conversation with tags
        conversation_id = await self._save_conversation_with_tags(
            user=user,
            request=request,
            response=response_message,
            tag_result=tag_result,
            context=context
        )
        
        # 7. Update user knowledge profile
        await self.user_knowledge_service.update_user_profile_with_tags(
            user_id=user.id,
            data_type="message",
            tags=tag_result.tags,
            confidence=tag_result.confidence,
            additional_context={
                "message_type": "user_input",
                "agent_type": request.agent_type,
                "conversation_id": conversation_id
            }
        )
        
        # 8. Publish domain events
        await self._publish_tagging_events(user, tag_result, conversation_id)
        
        return ChatResponse(
            message=response_message,
            agent_type=request.agent_type,
            user_message=request.message,
            conversation_id=conversation_id,
            context_used=context
        )
    
    async def _get_and_validate_user(self, user_id: UUID) -> User:
        """Get user and validate existence"""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User {user_id} not found")
        
        if not user.is_active:
            raise UserNotFoundException(f"User {user_id} is not active")
        
        return user
    
    async def _build_intelligent_context(
        self, 
        user: User, 
        request: ChatRequest,
        tag_result: TagExtractionResult
    ) -> Dict[str, Any]:
        """Build intelligent context using user knowledge and tag-based insights"""
        
        # Start with enhanced user knowledge context
        context = await self.user_knowledge_service.get_personalization_context(
            user.id, "chat"
        )
        
        # Add current message tags and insights
        context["current_tags"] = tag_result.tags
        context["current_insights"] = tag_result.insights
        context["tag_confidence"] = tag_result.confidence
        context["tag_categories"] = tag_result.categories
        
        # Find similar past experiences based on current tags
        similar_experiences = await self.similarity_search_service.find_similar_content(
            user_id=user.id,
            reference_tags=tag_result.tags,
            content_types=["message", "emotional_record"],
            time_range_days=90,
            limit=5
        )
        context["similar_past_experiences"] = [
            {
                "type": exp.item_type,
                "similarity": exp.similarity_score,
                "matching_tags": exp.matching_tags,
                "summary": exp.content_summary,
                "date": exp.created_at.isoformat()
            }
            for exp in similar_experiences
        ]
        
        # Get effective coping strategies for current situation
        if any(category in ["emotional", "stress"] for category in tag_result.categories.keys()):
            coping_strategies = await self.similarity_search_service.find_effective_coping_strategies(
                user_id=user.id,
                situation_tags=tag_result.tags,
                min_effectiveness=3
            )
            context["effective_coping_strategies"] = coping_strategies
        
        # Get user behavioral patterns relevant to current tags
        behavioral_patterns = await self.user_knowledge_service.analyze_behavioral_patterns(
            user_id=user.id,
            time_period_days=30
        )
        context["behavioral_patterns"] = behavioral_patterns
        
        # Add trending tags to understand user's current focus areas
        trending_tags = await self.similarity_search_service.get_trending_tags_for_user(
            user_id=user.id,
            time_range_days=7
        )
        context["trending_topics"] = [{"tag": tag, "trend": score} for tag, score in trending_tags[:5]]
        
        # Get wellness recommendations based on current context
        recommendations = await self.user_knowledge_service.get_wellness_recommendations(
            user_id=user.id,
            current_context={
                "tags": tag_result.tags,
                "categories": tag_result.categories,
                "message": request.message
            }
        )
        context["personalized_recommendations"] = recommendations
        
        # Add any additional context from the request
        if request.context:
            context.update(request.context)
        
        return context
    
    async def _save_conversation_with_tags(
        self,
        user: User,
        request: ChatRequest,
        response: str,
        tag_result: TagExtractionResult,
        context: Dict[str, Any]
    ) -> str:
        """Save conversation with intelligent tagging information"""
        
        conversation_data = {
            "user_message": request.message,
            "agent_response": response,
            "agent_type": request.agent_type,
            "tags": tag_result.tags,
            "tag_confidence": tag_result.confidence,
            "tag_categories": tag_result.categories,
            "extracted_insights": tag_result.insights,
            "context_summary": self._summarize_intelligent_context(context),
            "user_profile_completeness": context.get("profile_completeness", 0),
            "personality_used": user.agent_personality.value,
            "similar_experiences_count": len(context.get("similar_past_experiences", [])),
            "recommendations_provided": len(context.get("personalized_recommendations", []))
        }
        
        return await self.conversation_repository.save_conversation(
            user_id=user.id,
            agent_type=request.agent_type,
            conversation_data=conversation_data
        )
    
    async def _publish_tagging_events(
        self,
        user: User,
        tag_result: TagExtractionResult,
        conversation_id: str
    ) -> None:
        """Publish domain events for intelligent tagging and conversation"""
        
        # Publish conversation started event
        conversation_event = AgentConversationStartedEvent(
            user_id=user.id,
            agent_type="intelligent_agent",  # Updated for new system
            session_id=conversation_id
        )
        await self.event_repository.save_event(conversation_event)
        
        # Publish user data tagged event
        tagging_event = UserDataTaggedEvent(
            user_id=user.id,
            data_type="message",
            data_id=conversation_id,
            extracted_tags=tag_result.tags,
            tag_confidence=tag_result.confidence
        )
        await self.event_repository.save_event(tagging_event)
    
    def _summarize_intelligent_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of intelligent context for storage"""
        return {
            "current_tags_count": len(context.get("current_tags", [])),
            "tag_confidence": context.get("tag_confidence", 0.0),
            "insights_generated": len(context.get("current_insights", [])),
            "similar_experiences_found": len(context.get("similar_past_experiences", [])),
            "coping_strategies_available": len(context.get("effective_coping_strategies", [])),
            "behavioral_patterns_analyzed": bool(context.get("behavioral_patterns")),
            "trending_topics_count": len(context.get("trending_topics", [])),
            "recommendations_count": len(context.get("personalized_recommendations", [])),
            "tag_categories": list(context.get("tag_categories", {}).keys())
        } 