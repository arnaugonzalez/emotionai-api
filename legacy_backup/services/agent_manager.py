from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import logging
from sqlalchemy.orm import Session

from agents.therapy_agent import TherapyAgent
from agents.wellness_agent import WellnessAgent
from core.llm_factory import LLMFactory
from app.models import User, EmotionalRecord, BreathingSession
from app.config import settings

logger = logging.getLogger(__name__)

class AgentManager:
    """Manages personalized agents for all users"""
    
    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
        self.active_agents: Dict[int, Dict[str, Any]] = {}  # user_id -> {agent_type -> agent}
        self.agent_classes = {
            'therapy': TherapyAgent,
            'wellness': WellnessAgent
        }
        
        # Cleanup task
        self._cleanup_task = None
        self._start_cleanup_task()
        
        logger.info("Initialized AgentManager")
    
    def _start_cleanup_task(self):
        """Start background task for agent cleanup"""
        async def cleanup_inactive_agents():
            while True:
                try:
                    await asyncio.sleep(settings.memory_cleanup_interval)
                    await self._cleanup_inactive_agents()
                except Exception as e:
                    logger.error(f"Error in cleanup task: {e}")
        
        self._cleanup_task = asyncio.create_task(cleanup_inactive_agents())
    
    async def get_agent(
        self, 
        user_id: int, 
        agent_type: str = 'therapy',
        db_session: Optional[Session] = None
    ) -> Optional[Any]:
        """Get or create an agent for a user"""
        try:
            # Check if agent already exists and is active
            if user_id in self.active_agents and agent_type in self.active_agents[user_id]:
                agent = self.active_agents[user_id][agent_type]
                if agent.is_active():
                    return agent
                else:
                    # Agent is inactive, remove it
                    del self.active_agents[user_id][agent_type]
                    if not self.active_agents[user_id]:
                        del self.active_agents[user_id]
            
            # Create new agent
            agent = await self._create_agent(user_id, agent_type, db_session)
            
            # Store in active agents
            if user_id not in self.active_agents:
                self.active_agents[user_id] = {}
            self.active_agents[user_id][agent_type] = agent
            
            logger.info(f"Created {agent_type} agent for user {user_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Error getting agent for user {user_id}: {e}")
            return None
    
    async def _create_agent(
        self, 
        user_id: int, 
        agent_type: str,
        db_session: Optional[Session] = None
    ) -> Any:
        """Create a new agent instance"""
        if agent_type not in self.agent_classes:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Get LLM instance
        llm = await self.llm_factory.get_llm()
        
        # Get user data for personalization
        user_data = await self._get_user_data(user_id, db_session) if db_session else {}
        
        # Create agent
        agent_class = self.agent_classes[agent_type]
        agent = agent_class(
            user_id=user_id,
            llm=llm,
            personality=user_data.get('personality', 'empathetic_supportive'),
            memory_window=settings.max_memory_items
        )
        
        # Initialize agent with user data
        if user_data:
            agent.set_user_profile(user_data.get('profile_data', {}))
            agent.set_preferences(user_data.get('agent_preferences', {}))
            agent.process_user_data(user_data)
        
        return agent
    
    async def _get_user_data(self, user_id: int, db_session: Session) -> Dict[str, Any]:
        """Fetch user data from database for agent initialization"""
        try:
            # Get user profile
            user = db_session.query(User).filter(User.id == user_id).first()
            if not user:
                return {}
            
            # Get emotional records (last 30 days)
            thirty_days_ago = datetime.now() - timedelta(days=30)
            emotional_records = db_session.query(EmotionalRecord).filter(
                EmotionalRecord.user_id == user_id,
                EmotionalRecord.recorded_at >= thirty_days_ago
            ).order_by(EmotionalRecord.recorded_at.desc()).limit(50).all()
            
            # Get breathing sessions (last 30 days)
            breathing_sessions = db_session.query(BreathingSession).filter(
                BreathingSession.user_id == user_id,
                BreathingSession.created_at >= thirty_days_ago
            ).order_by(BreathingSession.created_at.desc()).limit(20).all()
            
            # Convert to dictionaries
            user_data = {
                'personality': user.agent_personality,
                'profile_data': user.profile_data or {},
                'agent_preferences': user.agent_preferences or {},
                'emotional_records': [
                    {
                        'emotion_type': record.emotion_type,
                        'intensity': record.intensity,
                        'context': record.context,
                        'recorded_at': record.recorded_at.isoformat()
                    } for record in emotional_records
                ],
                'breathing_sessions': [
                    {
                        'pattern_name': session.pattern_name,
                        'duration_seconds': session.duration_seconds,
                        'session_data': session.session_data or {},
                        'created_at': session.created_at.isoformat()
                    } for session in breathing_sessions
                ]
            }
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error fetching user data for user {user_id}: {e}")
            return {}
    
    async def update_agent_context(
        self, 
        user_id: int, 
        context_data: Dict[str, Any],
        agent_type: str = 'therapy'
    ) -> bool:
        """Update agent context with new information"""
        try:
            if user_id in self.active_agents and agent_type in self.active_agents[user_id]:
                agent = self.active_agents[user_id][agent_type]
                agent.update_context(context_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating agent context for user {user_id}: {e}")
            return False
    
    async def add_emotional_record(
        self, 
        user_id: int, 
        emotion_data: Dict[str, Any],
        agent_type: str = 'therapy'
    ) -> bool:
        """Add emotional record to agent's understanding"""
        try:
            if user_id in self.active_agents and agent_type in self.active_agents[user_id]:
                agent = self.active_agents[user_id][agent_type]
                agent.add_emotional_record(emotion_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding emotional record for user {user_id}: {e}")
            return False
    
    async def add_breathing_session(
        self, 
        user_id: int, 
        session_data: Dict[str, Any],
        agent_type: str = 'therapy'
    ) -> bool:
        """Add breathing session to agent's understanding"""
        try:
            if user_id in self.active_agents and agent_type in self.active_agents[user_id]:
                agent = self.active_agents[user_id][agent_type]
                agent.add_breathing_session(session_data)
                return True
            return False
        except Exception as e:
            logger.error(f"Error adding breathing session for user {user_id}: {e}")
            return False
    
    async def process_message(
        self, 
        user_id: int, 
        message: str,
        agent_type: str = 'therapy',
        context: Optional[Dict[str, Any]] = None,
        db_session: Optional[Session] = None
    ) -> Optional[str]:
        """Process a message with user's agent"""
        try:
            # Get or create agent
            agent = await self.get_agent(user_id, agent_type, db_session)
            if not agent:
                return "Sorry, I'm unable to process your message right now. Please try again later."
            
            # Process message with timeout
            response = await asyncio.wait_for(
                agent.process_message(message, context),
                timeout=settings.agent_timeout
            )
            
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Agent timeout for user {user_id}")
            return "I'm taking a bit longer to respond than usual. Please try again."
        except Exception as e:
            logger.error(f"Error processing message for user {user_id}: {e}")
            return "I'm sorry, I encountered an error while processing your message. Please try again."
    
    async def clear_agent_memory(self, user_id: int, agent_type: str = 'therapy') -> bool:
        """Clear agent's conversation memory"""
        try:
            if user_id in self.active_agents and agent_type in self.active_agents[user_id]:
                agent = self.active_agents[user_id][agent_type]
                agent.clear_memory()
                logger.info(f"Cleared memory for user {user_id} agent {agent_type}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing agent memory for user {user_id}: {e}")
            return False
    
    async def get_agent_status(self, user_id: int, agent_type: str = 'therapy') -> Dict[str, Any]:
        """Get agent status and metadata"""
        try:
            if user_id in self.active_agents and agent_type in self.active_agents[user_id]:
                agent = self.active_agents[user_id][agent_type]
                return {
                    'active': agent.is_active(),
                    'last_interaction': agent.last_interaction.isoformat() if agent.last_interaction else None,
                    'memory_summary': agent.get_memory_summary(),
                    'personality': agent.personality,
                    'conversation_length': len(agent.conversation_history)
                }
            return {'active': False}
        except Exception as e:
            logger.error(f"Error getting agent status for user {user_id}: {e}")
            return {'active': False, 'error': str(e)}
    
    async def _cleanup_inactive_agents(self):
        """Remove inactive agents to free memory"""
        try:
            inactive_users = []
            
            for user_id, user_agents in self.active_agents.items():
                inactive_agent_types = []
                
                for agent_type, agent in user_agents.items():
                    if not agent.is_active():
                        inactive_agent_types.append(agent_type)
                
                # Remove inactive agents
                for agent_type in inactive_agent_types:
                    del user_agents[agent_type]
                    logger.debug(f"Cleaned up inactive {agent_type} agent for user {user_id}")
                
                # If no agents left for user, mark for removal
                if not user_agents:
                    inactive_users.append(user_id)
            
            # Remove users with no active agents
            for user_id in inactive_users:
                del self.active_agents[user_id]
            
            if inactive_users:
                logger.info(f"Cleaned up agents for {len(inactive_users)} inactive users")
                
        except Exception as e:
            logger.error(f"Error during agent cleanup: {e}")
    
    def get_active_agent_count(self) -> Dict[str, int]:
        """Get count of active agents by type"""
        counts = {}
        for user_agents in self.active_agents.values():
            for agent_type in user_agents.keys():
                counts[agent_type] = counts.get(agent_type, 0) + 1
        
        return counts
    
    async def shutdown(self):
        """Shutdown agent manager and cleanup resources"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Clear all agents
        self.active_agents.clear()
        logger.info("AgentManager shutdown complete") 