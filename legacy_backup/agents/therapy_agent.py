from typing import Dict, Any, List, Optional
from .base_agent import BasePersonalizedAgent
from langchain.chat_models import ChatOpenAI
from langchain.tools import BaseTool
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

class TherapyAgent(BasePersonalizedAgent):
    """Specialized agent for therapeutic conversations and mental health support"""
    
    def __init__(
        self,
        user_id: int,
        llm: ChatOpenAI,
        personality: str = "empathetic_supportive",
        **kwargs
    ):
        super().__init__(user_id, llm, personality, **kwargs)
        
        # Therapy-specific attributes
        self.therapy_goals: List[str] = []
        self.coping_strategies: List[str] = []
        self.trigger_patterns: Dict[str, Any] = {}
        self.progress_notes: List[Dict[str, Any]] = []
        
        # Session tracking
        self.current_session_data: Dict[str, Any] = {}
        self.session_count: int = 0
        
        logger.info(f"Initialized TherapyAgent for user {user_id}")
    
    def get_system_prompt(self) -> str:
        """Return therapy-specific system prompt"""
        base_prompt = """You are a compassionate mental health support assistant. Your role is to provide empathetic, non-judgmental support while following these guidelines:

CORE PRINCIPLES:
- Always prioritize user safety and well-being
- Provide emotional support and validation
- Encourage healthy coping strategies
- Maintain appropriate therapeutic boundaries
- Never diagnose or provide medical advice
- Encourage professional help when appropriate

RESPONSE STYLE:
- Be warm, empathetic, and genuinely caring
- Use active listening techniques
- Ask thoughtful follow-up questions
- Validate emotions without judgment
- Offer gentle insights and perspectives
- Suggest practical coping strategies when appropriate

SAFETY PROTOCOLS:
- If user expresses suicidal thoughts, provide crisis resources immediately
- Recognize signs of severe mental health crises
- Encourage professional help for serious concerns
- Maintain confidentiality and respect boundaries

Remember: You are a supportive companion, not a replacement for professional mental health care."""
        
        # Add personality-specific modifications
        personality_additions = {
            "empathetic_supportive": "\nFocus on emotional validation and gentle support. Use phrases like 'I hear you' and 'That sounds really difficult.'",
            "encouraging_motivational": "\nEmphasize resilience and growth. Highlight user strengths and past successes.",
            "analytical_practical": "\nOffer structured approaches and concrete strategies. Help break down problems into manageable steps.",
            "mindful_contemplative": "\nEncourage present-moment awareness and self-reflection. Suggest mindfulness techniques.",
            "creative_expressive": "\nSuggest creative outlets for emotional expression. Encourage journaling, art, or other creative activities."
        }
        
        if self.personality in personality_additions:
            base_prompt += personality_additions[self.personality]
        
        return base_prompt
    
    def process_user_data(self, user_data: Dict[str, Any]) -> None:
        """Process therapy-specific user data"""
        # Update therapy goals
        if 'therapy_goals' in user_data:
            self.therapy_goals = user_data['therapy_goals']
        
        # Update coping strategies
        if 'coping_strategies' in user_data:
            self.coping_strategies = user_data['coping_strategies']
        
        # Process emotional patterns
        if 'emotional_records' in user_data:
            self._analyze_emotional_patterns(user_data['emotional_records'])
        
        # Update progress notes
        if 'progress_notes' in user_data:
            self.progress_notes.extend(user_data['progress_notes'])
        
        logger.debug(f"Processed therapy data for user {self.user_id}")
    
    def _analyze_emotional_patterns(self, emotional_records: List[Dict[str, Any]]) -> None:
        """Analyze emotional patterns from records"""
        if not emotional_records:
            return
        
        # Analyze intensity patterns
        recent_records = emotional_records[-10:]  # Last 10 records
        
        emotion_counts = {}
        intensity_sum = 0
        high_intensity_count = 0
        
        for record in recent_records:
            emotion_type = record.get('emotion_type', 'unknown')
            intensity = record.get('intensity', 0)
            
            emotion_counts[emotion_type] = emotion_counts.get(emotion_type, 0) + 1
            intensity_sum += intensity
            
            if intensity >= 8:
                high_intensity_count += 1
        
        # Store patterns
        self.trigger_patterns = {
            'most_common_emotions': sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:3],
            'average_intensity': intensity_sum / len(recent_records) if recent_records else 0,
            'high_intensity_frequency': high_intensity_count / len(recent_records) if recent_records else 0,
            'last_updated': datetime.now().isoformat()
        }
    
    def start_therapy_session(self, session_type: str = "general") -> Dict[str, Any]:
        """Start a new therapy session"""
        self.session_count += 1
        self.current_session_data = {
            'session_id': f"session_{self.user_id}_{self.session_count}",
            'session_type': session_type,
            'start_time': datetime.now().isoformat(),
            'topics_discussed': [],
            'coping_strategies_suggested': [],
            'user_insights': [],
            'mood_before': None,
            'mood_after': None
        }
        
        logger.info(f"Started therapy session {self.current_session_data['session_id']}")
        return self.current_session_data
    
    def end_therapy_session(self, session_summary: Optional[str] = None) -> Dict[str, Any]:
        """End current therapy session and save summary"""
        if not self.current_session_data:
            return {}
        
        self.current_session_data.update({
            'end_time': datetime.now().isoformat(),
            'session_summary': session_summary or self._generate_session_summary(),
            'status': 'completed'
        })
        
        # Add to progress notes
        self.progress_notes.append(self.current_session_data.copy())
        
        # Keep only recent progress notes
        if len(self.progress_notes) > 50:
            self.progress_notes = self.progress_notes[-50:]
        
        session_data = self.current_session_data.copy()
        self.current_session_data = {}
        
        logger.info(f"Ended therapy session {session_data['session_id']}")
        return session_data
    
    def _generate_session_summary(self) -> str:
        """Generate an automatic session summary"""
        if not self.current_session_data:
            return "No session data available"
        
        topics = self.current_session_data.get('topics_discussed', [])
        strategies = self.current_session_data.get('coping_strategies_suggested', [])
        insights = self.current_session_data.get('user_insights', [])
        
        summary_parts = []
        
        if topics:
            summary_parts.append(f"Topics discussed: {', '.join(topics[:3])}")
        
        if strategies:
            summary_parts.append(f"Strategies suggested: {', '.join(strategies[:2])}")
        
        if insights:
            summary_parts.append(f"User insights: {', '.join(insights[:2])}")
        
        return "; ".join(summary_parts) if summary_parts else "General therapeutic conversation"
    
    def add_session_topic(self, topic: str) -> None:
        """Add a topic to current session"""
        if self.current_session_data and 'topics_discussed' in self.current_session_data:
            if topic not in self.current_session_data['topics_discussed']:
                self.current_session_data['topics_discussed'].append(topic)
    
    def suggest_coping_strategy(self, strategy: str) -> None:
        """Record a suggested coping strategy"""
        if self.current_session_data and 'coping_strategies_suggested' in self.current_session_data:
            if strategy not in self.current_session_data['coping_strategies_suggested']:
                self.current_session_data['coping_strategies_suggested'].append(strategy)
        
        # Also add to user's known strategies
        if strategy not in self.coping_strategies:
            self.coping_strategies.append(strategy)
    
    def record_user_insight(self, insight: str) -> None:
        """Record a user insight during session"""
        if self.current_session_data and 'user_insights' in self.current_session_data:
            self.current_session_data['user_insights'].append(insight)
    
    def get_therapy_context(self) -> str:
        """Get therapy-specific context for responses"""
        context_parts = []
        
        # Current therapy goals
        if self.therapy_goals:
            context_parts.append(f"Therapy goals: {', '.join(self.therapy_goals)}")
        
        # Known coping strategies
        if self.coping_strategies:
            context_parts.append(f"Known coping strategies: {', '.join(self.coping_strategies[:5])}")
        
        # Emotional patterns
        if self.trigger_patterns:
            most_common = self.trigger_patterns.get('most_common_emotions', [])
            if most_common:
                emotions = [emotion for emotion, count in most_common]
                context_parts.append(f"Common emotions: {', '.join(emotions)}")
            
            avg_intensity = self.trigger_patterns.get('average_intensity', 0)
            if avg_intensity > 0:
                context_parts.append(f"Average emotional intensity: {avg_intensity:.1f}/10")
        
        # Recent progress
        if self.progress_notes:
            recent_session = self.progress_notes[-1]
            context_parts.append(f"Last session: {recent_session.get('session_summary', 'No summary')}")
        
        return "\n".join(context_parts)
    
    def get_crisis_response(self) -> str:
        """Get crisis intervention response"""
        return """I'm very concerned about what you're sharing with me. Your safety is the most important thing right now.

Please reach out for immediate help:
• National Suicide Prevention Lifeline: 988
• Crisis Text Line: Text HOME to 741741
• Emergency Services: 911

You don't have to go through this alone. There are people who want to help you right now. Please reach out to one of these resources immediately.

Is there a trusted friend, family member, or mental health professional you can contact right now?"""
    
    def assess_crisis_risk(self, message: str) -> bool:
        """Simple keyword-based crisis assessment"""
        crisis_keywords = [
            'suicide', 'kill myself', 'end it all', 'not worth living',
            'hurt myself', 'self harm', 'want to die', 'better off dead'
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in crisis_keywords)
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Override to add therapy-specific processing"""
        # Check for crisis content first
        if self.assess_crisis_risk(message):
            logger.warning(f"Crisis content detected for user {self.user_id}")
            return self.get_crisis_response()
        
        # Add therapy context
        if context is None:
            context = {}
        
        therapy_context = self.get_therapy_context()
        if therapy_context:
            context['therapy_context'] = therapy_context
        
        # Process with base agent
        response = await super().process_message(message, context)
        
        # Post-process for therapy insights
        self._extract_session_insights(message, response)
        
        return response
    
    def _extract_session_insights(self, user_message: str, agent_response: str) -> None:
        """Extract insights from conversation for session tracking"""
        if not self.current_session_data:
            return
        
        # Simple keyword extraction for topics
        topic_keywords = {
            'anxiety': ['anxiety', 'anxious', 'worried', 'stress', 'nervous'],
            'depression': ['depression', 'depressed', 'sad', 'hopeless', 'empty'],
            'relationships': ['relationship', 'partner', 'family', 'friend', 'social'],
            'work': ['work', 'job', 'career', 'colleague', 'boss'],
            'self_esteem': ['confidence', 'self-worth', 'worthless', 'failure'],
            'trauma': ['trauma', 'ptsd', 'flashback', 'triggered']
        }
        
        message_lower = user_message.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                self.add_session_topic(topic)
        
        # Extract suggested strategies from agent response
        strategy_keywords = {
            'breathing exercises': ['breathing', 'breathe', 'inhale', 'exhale'],
            'mindfulness': ['mindfulness', 'present moment', 'mindful', 'meditation'],
            'journaling': ['journal', 'write', 'writing', 'diary'],
            'exercise': ['exercise', 'walk', 'physical activity', 'movement'],
            'social support': ['talk to someone', 'reach out', 'support', 'friend']
        }
        
        response_lower = agent_response.lower()
        for strategy, keywords in strategy_keywords.items():
            if any(keyword in response_lower for keyword in keywords):
                self.suggest_coping_strategy(strategy) 