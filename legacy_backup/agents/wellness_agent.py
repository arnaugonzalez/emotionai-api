from typing import Dict, Any, List, Optional
from .base_agent import BasePersonalizedAgent
from langchain.chat_models import ChatOpenAI
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class WellnessAgent(BasePersonalizedAgent):
    """Specialized agent for general wellness, mindfulness, and self-care support"""
    
    def __init__(
        self,
        user_id: int,
        llm: ChatOpenAI,
        personality: str = "mindful_contemplative",
        **kwargs
    ):
        super().__init__(user_id, llm, personality, **kwargs)
        
        # Wellness-specific attributes
        self.wellness_goals: List[str] = []
        self.mindfulness_practices: List[str] = []
        self.self_care_activities: List[str] = []
        self.wellness_routines: Dict[str, Any] = {}
        
        # Wellness tracking
        self.wellness_metrics: Dict[str, Any] = {}
        self.mood_trends: List[Dict[str, Any]] = []
        
        logger.info(f"Initialized WellnessAgent for user {user_id}")
    
    def get_system_prompt(self) -> str:
        """Return wellness-specific system prompt"""
        base_prompt = """You are a supportive wellness and mindfulness companion. Your role is to promote overall well-being, mental health, and personal growth through:

CORE FOCUS AREAS:
- Mindfulness and meditation practices
- Stress management and relaxation techniques
- Healthy lifestyle habits and routines
- Emotional regulation and self-awareness
- Personal growth and self-improvement
- Work-life balance and boundary setting

RESPONSE APPROACH:
- Encourage mindful awareness of thoughts and feelings
- Suggest practical wellness activities and techniques
- Support the development of healthy habits
- Promote self-compassion and acceptance
- Offer gentle guidance on lifestyle improvements
- Help build resilience and coping skills

WELLNESS STRATEGIES:
- Breathing exercises and meditation techniques
- Physical activity and movement suggestions
- Sleep hygiene and rest recommendations
- Nutrition and hydration awareness
- Social connection and community building
- Creative expression and hobbies

Always maintain a supportive, non-judgmental tone and remember that small, consistent steps lead to lasting wellness improvements."""
        
        # Add personality-specific modifications
        personality_additions = {
            "mindful_contemplative": "\nEmphasize present-moment awareness and gentle self-reflection. Guide users to observe their thoughts and feelings without judgment.",
            "encouraging_motivational": "\nFocus on celebrating small wins and building momentum. Highlight progress and potential for growth.",
            "empathetic_supportive": "\nProvide warm validation and understanding. Create a safe space for users to explore their wellness journey.",
            "analytical_practical": "\nOffer structured approaches to wellness. Provide clear steps and measurable goals for improvement.",
            "creative_expressive": "\nSuggest creative and artistic approaches to wellness. Encourage exploration through art, music, writing, or movement."
        }
        
        if self.personality in personality_additions:
            base_prompt += personality_additions[self.personality]
        
        return base_prompt
    
    def process_user_data(self, user_data: Dict[str, Any]) -> None:
        """Process wellness-specific user data"""
        # Update wellness goals
        if 'wellness_goals' in user_data:
            self.wellness_goals = user_data['wellness_goals']
        
        # Update mindfulness practices
        if 'mindfulness_practices' in user_data:
            self.mindfulness_practices = user_data['mindfulness_practices']
        
        # Update self-care activities
        if 'self_care_activities' in user_data:
            self.self_care_activities = user_data['self_care_activities']
        
        # Process breathing sessions for wellness insights
        if 'breathing_sessions' in user_data:
            self._analyze_breathing_patterns(user_data['breathing_sessions'])
        
        # Process emotional records for mood trends
        if 'emotional_records' in user_data:
            self._analyze_mood_trends(user_data['emotional_records'])
        
        logger.debug(f"Processed wellness data for user {self.user_id}")
    
    def _analyze_breathing_patterns(self, breathing_sessions: List[Dict[str, Any]]) -> None:
        """Analyze breathing session patterns for wellness insights"""
        if not breathing_sessions:
            return
        
        recent_sessions = breathing_sessions[-10:]  # Last 10 sessions
        
        total_sessions = len(recent_sessions)
        total_duration = sum(session.get('duration_seconds', 0) for session in recent_sessions)
        pattern_usage = {}
        
        for session in recent_sessions:
            pattern = session.get('pattern_name', 'unknown')
            pattern_usage[pattern] = pattern_usage.get(pattern, 0) + 1
        
        self.wellness_metrics['breathing_practice'] = {
            'total_sessions_recent': total_sessions,
            'total_duration_minutes': total_duration / 60,
            'average_session_length': (total_duration / total_sessions) if total_sessions > 0 else 0,
            'most_used_patterns': sorted(pattern_usage.items(), key=lambda x: x[1], reverse=True)[:3],
            'last_updated': datetime.now().isoformat()
        }
    
    def _analyze_mood_trends(self, emotional_records: List[Dict[str, Any]]) -> None:
        """Analyze mood trends for wellness insights"""
        if not emotional_records:
            return
        
        recent_records = emotional_records[-14:]  # Last 14 records for trend analysis
        
        # Calculate mood stability and trends
        intensities = [record.get('intensity', 0) for record in recent_records]
        emotions = [record.get('emotion_type', '') for record in recent_records]
        
        if intensities:
            avg_intensity = sum(intensities) / len(intensities)
            intensity_variance = sum((x - avg_intensity) ** 2 for x in intensities) / len(intensities)
            
            # Simple trend calculation (last 7 vs previous 7)
            if len(intensities) >= 14:
                recent_avg = sum(intensities[-7:]) / 7
                previous_avg = sum(intensities[-14:-7]) / 7
                trend = "improving" if recent_avg < previous_avg else "stable" if abs(recent_avg - previous_avg) < 0.5 else "challenging"
            else:
                trend = "insufficient_data"
            
            self.mood_trends = [{
                'period': 'last_14_days',
                'average_intensity': avg_intensity,
                'mood_stability': "stable" if intensity_variance < 2 else "variable",
                'trend': trend,
                'most_common_emotions': list(set(emotions)),
                'last_updated': datetime.now().isoformat()
            }]
    
    def suggest_wellness_activity(self, activity_type: str = "general") -> str:
        """Suggest wellness activities based on type"""
        activities = {
            "mindfulness": [
                "Take 5 minutes for deep breathing",
                "Practice a brief body scan meditation",
                "Try mindful walking for 10 minutes",
                "Engage in mindful eating during your next meal"
            ],
            "physical": [
                "Take a 10-minute walk outside",
                "Do some gentle stretching",
                "Try a few yoga poses",
                "Dance to your favorite song"
            ],
            "relaxation": [
                "Take a warm bath or shower",
                "Listen to calming music",
                "Practice progressive muscle relaxation",
                "Try some gentle self-massage"
            ],
            "creative": [
                "Write in a journal for 10 minutes",
                "Draw or doodle something",
                "Take photos of things that bring you joy",
                "Try a creative writing exercise"
            ],
            "social": [
                "Reach out to a friend or family member",
                "Practice gratitude by thanking someone",
                "Join a community activity",
                "Share something positive with others"
            ],
            "general": [
                "Take three deep breaths",
                "Look out the window and notice nature",
                "Think of three things you're grateful for",
                "Give yourself a gentle, encouraging thought"
            ]
        }
        
        import random
        activity_list = activities.get(activity_type, activities["general"])
        return random.choice(activity_list)
    
    def get_wellness_context(self) -> str:
        """Get wellness-specific context for responses"""
        context_parts = []
        
        # Wellness goals
        if self.wellness_goals:
            context_parts.append(f"Wellness goals: {', '.join(self.wellness_goals)}")
        
        # Current mindfulness practices
        if self.mindfulness_practices:
            context_parts.append(f"Current practices: {', '.join(self.mindfulness_practices)}")
        
        # Breathing practice insights
        if 'breathing_practice' in self.wellness_metrics:
            bp = self.wellness_metrics['breathing_practice']
            context_parts.append(f"Breathing practice: {bp['total_sessions_recent']} recent sessions, {bp['total_duration_minutes']:.1f} total minutes")
        
        # Mood trends
        if self.mood_trends:
            trend = self.mood_trends[0]
            context_parts.append(f"Mood trend: {trend['trend']}, average intensity: {trend['average_intensity']:.1f}/10")
        
        return "\n".join(context_parts)
    
    async def process_message(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Override to add wellness-specific processing"""
        # Add wellness context
        if context is None:
            context = {}
        
        wellness_context = self.get_wellness_context()
        if wellness_context:
            context['wellness_context'] = wellness_context
        
        # Check for specific wellness requests
        message_lower = message.lower()
        
        # Suggest activities based on message content
        if any(word in message_lower for word in ['stressed', 'anxious', 'overwhelmed']):
            activity_suggestion = self.suggest_wellness_activity("relaxation")
            context['suggested_activity'] = f"Consider trying: {activity_suggestion}"
        elif any(word in message_lower for word in ['tired', 'low energy', 'sluggish']):
            activity_suggestion = self.suggest_wellness_activity("physical")
            context['suggested_activity'] = f"Consider trying: {activity_suggestion}"
        elif any(word in message_lower for word in ['lonely', 'isolated', 'disconnected']):
            activity_suggestion = self.suggest_wellness_activity("social")
            context['suggested_activity'] = f"Consider trying: {activity_suggestion}"
        elif any(word in message_lower for word in ['mindful', 'meditation', 'present']):
            activity_suggestion = self.suggest_wellness_activity("mindfulness")
            context['suggested_activity'] = f"Consider trying: {activity_suggestion}"
        
        # Process with base agent
        response = await super().process_message(message, context)
        
        return response
    
    def add_wellness_routine(self, routine_name: str, routine_data: Dict[str, Any]) -> None:
        """Add a wellness routine to the agent's knowledge"""
        self.wellness_routines[routine_name] = {
            **routine_data,
            'added_date': datetime.now().isoformat()
        }
        
        logger.debug(f"Added wellness routine '{routine_name}' for user {self.user_id}")
    
    def get_wellness_suggestions(self, focus_area: str = "general") -> List[str]:
        """Get personalized wellness suggestions"""
        suggestions = {
            "stress_management": [
                "Practice the 4-7-8 breathing technique",
                "Try a 10-minute guided meditation",
                "Take a mindful walk in nature",
                "Use progressive muscle relaxation"
            ],
            "sleep_hygiene": [
                "Create a relaxing bedtime routine",
                "Limit screen time before bed",
                "Try some gentle stretches before sleep",
                "Practice gratitude journaling before bed"
            ],
            "emotional_regulation": [
                "Name and acknowledge your current emotions",
                "Practice the STOP technique (Stop, Take a breath, Observe, Proceed)",
                "Use a feelings wheel to identify specific emotions",
                "Try the 5-4-3-2-1 grounding technique"
            ],
            "general": [
                "Take regular breaks throughout your day",
                "Practice gratitude by noting three positive things",
                "Stay hydrated and eat nourishing foods",
                "Connect with someone you care about"
            ]
        }
        
        return suggestions.get(focus_area, suggestions["general"]) 