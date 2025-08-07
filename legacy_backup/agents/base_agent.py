from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationSummaryBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.schema.runnable import Runnable
from langchain.tools import BaseTool
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)

class BasePersonalizedAgent(ABC):
    """Base class for all personalized mental health agents"""
    
    def __init__(
        self,
        user_id: int,
        llm: ChatOpenAI,
        personality: str = "empathetic_supportive",
        memory_window: int = 10,
        max_tokens: int = 500
    ):
        self.user_id = user_id
        self.llm = llm
        self.personality = personality
        self.memory_window = memory_window
        self.max_tokens = max_tokens
        
        # Initialize memory
        self.memory = ConversationSummaryBufferMemory(
            llm=llm,
            max_token_limit=1000,
            return_messages=True
        )
        
        # Agent tools and capabilities
        self.tools: List[BaseTool] = []
        self.context_data: Dict[str, Any] = {}
        
        # Conversation state
        self.conversation_history: List[BaseMessage] = []
        self.last_interaction: Optional[datetime] = None
        
        # Personalization data
        self.user_profile: Dict[str, Any] = {}
        self.emotional_patterns: Dict[str, Any] = {}
        self.preferences: Dict[str, Any] = {}
        
        logger.info(f"Initialized {self.__class__.__name__} for user {user_id}")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt specific to this agent type"""
        pass
    
    @abstractmethod
    def process_user_data(self, user_data: Dict[str, Any]) -> None:
        """Process and store user-specific data for personalization"""
        pass
    
    def update_context(self, context: Dict[str, Any]) -> None:
        """Update the agent's context with new information"""
        self.context_data.update(context)
        logger.debug(f"Updated context for user {self.user_id}: {list(context.keys())}")
    
    def add_emotional_record(self, emotion_data: Dict[str, Any]) -> None:
        """Add emotional record to agent's understanding"""
        if 'emotional_history' not in self.context_data:
            self.context_data['emotional_history'] = []
        
        self.context_data['emotional_history'].append({
            **emotion_data,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only recent records
        if len(self.context_data['emotional_history']) > 20:
            self.context_data['emotional_history'] = self.context_data['emotional_history'][-20:]
    
    def add_breathing_session(self, session_data: Dict[str, Any]) -> None:
        """Add breathing session to agent's understanding"""
        if 'breathing_history' not in self.context_data:
            self.context_data['breathing_history'] = []
        
        self.context_data['breathing_history'].append({
            **session_data,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only recent sessions
        if len(self.context_data['breathing_history']) > 10:
            self.context_data['breathing_history'] = self.context_data['breathing_history'][-10:]
    
    def _build_personalized_context(self) -> str:
        """Build personalized context string from user data"""
        context_parts = []
        
        # User profile information
        if self.user_profile:
            context_parts.append(f"User Profile: {self._summarize_profile()}")
        
        # Recent emotional patterns
        if 'emotional_history' in self.context_data:
            recent_emotions = self.context_data['emotional_history'][-5:]
            if recent_emotions:
                emotions_summary = ", ".join([
                    f"{e['emotion_type']} (intensity: {e['intensity']})"
                    for e in recent_emotions
                ])
                context_parts.append(f"Recent emotions: {emotions_summary}")
        
        # Recent breathing sessions
        if 'breathing_history' in self.context_data:
            recent_sessions = self.context_data['breathing_history'][-3:]
            if recent_sessions:
                sessions_summary = ", ".join([
                    f"{s['pattern_name']} ({s['duration_seconds']}s)"
                    for s in recent_sessions
                ])
                context_parts.append(f"Recent breathing sessions: {sessions_summary}")
        
        # Preferences and personality
        personality_context = self._get_personality_context()
        if personality_context:
            context_parts.append(personality_context)
        
        return "\n".join(context_parts)
    
    def _summarize_profile(self) -> str:
        """Create a concise summary of user profile"""
        if not self.user_profile:
            return "No profile data available"
        
        summary_parts = []
        if 'goals' in self.user_profile:
            summary_parts.append(f"Goals: {', '.join(self.user_profile['goals'])}")
        if 'concerns' in self.user_profile:
            summary_parts.append(f"Concerns: {', '.join(self.user_profile['concerns'])}")
        if 'preferred_activities' in self.user_profile:
            summary_parts.append(f"Preferred activities: {', '.join(self.user_profile['preferred_activities'])}")
        
        return "; ".join(summary_parts) if summary_parts else "Basic profile"
    
    def _get_personality_context(self) -> str:
        """Get personality-specific context"""
        personality_prompts = {
            "empathetic_supportive": "Respond with deep empathy and unconditional support. Focus on validation and gentle guidance.",
            "encouraging_motivational": "Provide encouraging and motivational responses. Focus on strengths and positive reinforcement.",
            "analytical_practical": "Offer practical, analytical advice. Focus on concrete steps and logical solutions.",
            "mindful_contemplative": "Encourage mindfulness and self-reflection. Focus on present-moment awareness.",
            "creative_expressive": "Encourage creative expression and artistic approaches to emotional processing."
        }
        
        return personality_prompts.get(self.personality, personality_prompts["empathetic_supportive"])
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Process a user message and return agent response"""
        try:
            # Update context if provided
            if context:
                self.update_context(context)
            
            # Build the conversation messages
            messages = self._build_conversation_messages(message)
            
            # Get response from LLM
            response = await self._get_llm_response(messages)
            
            # Update conversation history
            self.conversation_history.append(HumanMessage(content=message))
            self.conversation_history.append(AIMessage(content=response))
            
            # Update memory
            self.memory.chat_memory.add_user_message(message)
            self.memory.chat_memory.add_ai_message(response)
            
            # Update last interaction
            self.last_interaction = datetime.now()
            
            logger.info(f"Processed message for user {self.user_id}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing message for user {self.user_id}: {e}")
            return "I'm sorry, I'm having trouble processing your message right now. Please try again."
    
    def _build_conversation_messages(self, current_message: str) -> List[BaseMessage]:
        """Build the complete conversation context for LLM"""
        messages = []
        
        # System prompt with personalization
        system_prompt = self.get_system_prompt()
        personalized_context = self._build_personalized_context()
        
        if personalized_context:
            system_prompt += f"\n\nPersonalized Context:\n{personalized_context}"
        
        messages.append(SystemMessage(content=system_prompt))
        
        # Add relevant conversation history
        if self.conversation_history:
            # Get recent messages within memory window
            recent_messages = self.conversation_history[-(self.memory_window * 2):]
            messages.extend(recent_messages)
        
        # Add current message
        messages.append(HumanMessage(content=current_message))
        
        return messages
    
    async def _get_llm_response(self, messages: List[BaseMessage]) -> str:
        """Get response from LLM with error handling"""
        try:
            response = await self.llm.agenerate([messages])
            return response.generations[0][0].text.strip()
        except Exception as e:
            logger.error(f"LLM error for user {self.user_id}: {e}")
            raise
    
    def clear_memory(self) -> None:
        """Clear agent's conversation memory"""
        self.memory.clear()
        self.conversation_history.clear()
        logger.info(f"Cleared memory for user {self.user_id}")
    
    def get_memory_summary(self) -> str:
        """Get a summary of the conversation memory"""
        if hasattr(self.memory, 'moving_summary_buffer') and self.memory.moving_summary_buffer:
            return self.memory.moving_summary_buffer
        return "No conversation history"
    
    def set_user_profile(self, profile_data: Dict[str, Any]) -> None:
        """Set user profile data"""
        self.user_profile = profile_data
        logger.debug(f"Updated user profile for user {self.user_id}")
    
    def set_preferences(self, preferences: Dict[str, Any]) -> None:
        """Set user preferences"""
        self.preferences = preferences
        logger.debug(f"Updated preferences for user {self.user_id}")
    
    def is_active(self) -> bool:
        """Check if agent has been recently active"""
        if not self.last_interaction:
            return False
        
        time_threshold = datetime.now() - timedelta(hours=24)
        return self.last_interaction > time_threshold 