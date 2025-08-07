"""
OpenAI-based Intelligent Tagging Service Implementation

This service uses OpenAI's GPT models to extract semantic tags from user content.
It provides intelligent content understanding for personalized user experiences.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID

import openai
from ...application.services.tagging_service import ITaggingService, TagExtractionResult


logger = logging.getLogger(__name__)


class OpenAITaggingService(ITaggingService):
    """OpenAI implementation of intelligent tagging service"""
    
    # Mental health urgency keywords (repurposed from crisis detection for tagging accuracy)
    MENTAL_HEALTH_URGENCY_KEYWORDS = [
        'suicide', 'kill myself', 'end it all', 'not worth living',
        'hurt myself', 'self harm', 'want to die', 'better off dead'
    ]
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        
        # System prompts for different content types
        self.message_system_prompt = """
You are an expert mental health AI that extracts semantic tags from user messages.

Extract 3-8 relevant tags that capture:
1. Emotional state (anxious, hopeful, frustrated, calm, etc.)
2. Behavioral patterns (seeking_help, avoidance, proactive, etc.)
3. Context/situation (work_stress, relationship_issues, health_concerns, etc.)
4. Mental health aspects (self_care, coping_strategies, triggers, mental_health_urgency, etc.)

Guidelines:
- Use lowercase with underscores for tags
- Be specific but not overly granular
- Focus on actionable and meaningful patterns
- Avoid redundant tags

Respond ONLY with a JSON object containing:
{
    "tags": ["tag1", "tag2", "tag3"],
    "confidence": 0.85,
    "categories": {
        "emotional": ["anxious", "hopeful"],
        "behavioral": ["seeking_help"],
        "contextual": ["work_stress"]
    },
    "insights": ["User is actively seeking coping strategies for work-related anxiety"]
}
"""
        
        self.emotional_system_prompt = """
You are an expert mental health AI that analyzes emotional records and extracts semantic tags.

Extract 3-6 relevant tags that capture:
1. Emotional patterns and triggers
2. Intensity patterns (mild, moderate, severe)
3. Situational context
4. Coping mechanisms mentioned

Guidelines:
- Use lowercase with underscores for tags
- Consider the emotion, intensity, and any triggers or notes
- Focus on patterns that could help with future recommendations

Respond ONLY with a JSON object containing:
{
    "tags": ["tag1", "tag2"],
    "confidence": 0.90,
    "categories": {
        "emotional": ["high_intensity_anxiety"],
        "triggers": ["social_situations"],
        "coping": ["breathing_exercises"]
    },
    "insights": ["High intensity anxiety triggered by social situations, responds well to breathing exercises"]
}
"""
        
        self.breathing_system_prompt = """
You are an expert mental health AI that analyzes breathing session data and extracts semantic tags.

Extract 3-5 relevant tags that capture:
1. Session effectiveness and patterns
2. User preferences
3. Context of use
4. Behavioral patterns

Guidelines:
- Use lowercase with underscores for tags
- Consider pattern type, duration, effectiveness, and notes
- Focus on what works for the user and when they use techniques

Respond ONLY with a JSON object containing:
{
    "tags": ["tag1", "tag2"],
    "confidence": 0.80,
    "categories": {
        "effectiveness": ["highly_effective"],
        "usage_pattern": ["stress_relief"],
        "preferences": ["short_sessions"]
    },
    "insights": ["User finds short breathing sessions highly effective for stress relief"]
}
"""
    
    async def extract_tags_from_message(
        self, 
        content: str, 
        user_context: Optional[Dict[str, Any]] = None
    ) -> TagExtractionResult:
        """Extract semantic tags from a chat message using OpenAI"""
        
        try:
            # Check for mental health urgency keywords (for enhanced tagging accuracy)
            content_lower = content.lower()
            has_urgency_keywords = any(keyword in content_lower for keyword in self.MENTAL_HEALTH_URGENCY_KEYWORDS)
            
            # Build user message with context
            user_message = f"Message content: {content}"
            if user_context:
                user_message += f"\n\nUser context: {json.dumps(user_context, indent=2)}"
            
            # Add urgency note if mental health urgency detected
            if has_urgency_keywords:
                user_message += "\n\nIMPORTANT: This message contains mental health urgency indicators. Please include tags like 'mental_health_urgency', 'immediate_support_needed', or 'therapeutic_intervention' with high confidence."
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.message_system_prompt},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            # Parse the JSON response
            result_text = response.choices[0].message.content.strip()
            result_data = json.loads(result_text)
            
            return TagExtractionResult(
                tags=result_data.get("tags", []),
                confidence=result_data.get("confidence", 0.0),
                categories=result_data.get("categories", {}),
                insights=result_data.get("insights", [])
            )
            
        except Exception as e:
            logger.error(f"Error extracting tags from message: {str(e)}")
            # Return fallback tags
            return TagExtractionResult(
                tags=["user_message", "needs_analysis"],
                confidence=0.1,
                categories={"fallback": ["user_message"]},
                insights=["Could not analyze message content"]
            )
    
    async def extract_tags_from_emotional_record(
        self,
        emotion: str,
        intensity: int,
        triggers: Optional[List[str]] = None,
        notes: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> TagExtractionResult:
        """Extract semantic tags from an emotional record"""
        
        try:
            # Build analysis content
            analysis_content = f"""
Emotion: {emotion}
Intensity: {intensity}/10
Triggers: {triggers or 'None specified'}
Notes: {notes or 'No additional notes'}
"""
            
            if user_context:
                analysis_content += f"\nUser context: {json.dumps(user_context, indent=2)}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.emotional_system_prompt},
                    {"role": "user", "content": analysis_content}
                ],
                max_tokens=250,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            result_data = json.loads(result_text)
            
            return TagExtractionResult(
                tags=result_data.get("tags", []),
                confidence=result_data.get("confidence", 0.0),
                categories=result_data.get("categories", {}),
                insights=result_data.get("insights", [])
            )
            
        except Exception as e:
            logger.error(f"Error extracting tags from emotional record: {str(e)}")
            return TagExtractionResult(
                tags=[f"{emotion.lower()}_emotion", f"intensity_{intensity}"],
                confidence=0.3,
                categories={"emotional": [f"{emotion.lower()}_emotion"]},
                insights=[f"Basic emotional record: {emotion} at intensity {intensity}"]
            )
    
    async def extract_tags_from_breathing_session(
        self,
        pattern_name: str,
        duration_minutes: int,
        effectiveness_rating: Optional[int] = None,
        notes: Optional[str] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> TagExtractionResult:
        """Extract semantic tags from a breathing session"""
        
        try:
            analysis_content = f"""
Breathing Pattern: {pattern_name}
Duration: {duration_minutes} minutes
Effectiveness Rating: {effectiveness_rating}/5 {'' if effectiveness_rating else '(Not rated)'}
Notes: {notes or 'No additional notes'}
"""
            
            if user_context:
                analysis_content += f"\nUser context: {json.dumps(user_context, indent=2)}"
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.breathing_system_prompt},
                    {"role": "user", "content": analysis_content}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            result_data = json.loads(result_text)
            
            return TagExtractionResult(
                tags=result_data.get("tags", []),
                confidence=result_data.get("confidence", 0.0),
                categories=result_data.get("categories", {}),
                insights=result_data.get("insights", [])
            )
            
        except Exception as e:
            logger.error(f"Error extracting tags from breathing session: {str(e)}")
            return TagExtractionResult(
                tags=["breathing_exercise", pattern_name.lower().replace(" ", "_")],
                confidence=0.3,
                categories={"activity": ["breathing_exercise"]},
                insights=[f"Breathing session: {pattern_name} for {duration_minutes} minutes"]
            )
    
    async def categorize_tags(self, tags: List[str]) -> Dict[str, List[str]]:
        """Categorize tags into semantic groups"""
        
        try:
            system_prompt = """
You are an expert at categorizing mental health and wellness tags.

Categorize the given tags into these groups:
- emotional: Tags related to emotions and feelings
- behavioral: Tags related to actions and behaviors
- contextual: Tags related to situations and environments
- coping: Tags related to coping strategies and techniques
- physical: Tags related to physical sensations or health
- social: Tags related to relationships and social interactions
- temporal: Tags related to time patterns or frequency

Respond ONLY with a JSON object mapping categories to tag lists.
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Tags to categorize: {json.dumps(tags)}"}
                ],
                max_tokens=200,
                temperature=0.2
            )
            
            result_text = response.choices[0].message.content.strip()
            return json.loads(result_text)
            
        except Exception as e:
            logger.error(f"Error categorizing tags: {str(e)}")
            return {"uncategorized": tags}
    
    async def find_similar_tags(
        self, 
        tag: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find semantically similar tags using OpenAI"""
        
        try:
            system_prompt = """
You are an expert at finding semantically similar mental health and wellness tags.

Given a tag, find similar tags that represent related concepts, emotions, or behaviors.
Include a similarity score (0.0 to 1.0) for each similar tag.

Respond ONLY with a JSON array of objects:
[
    {"tag": "similar_tag1", "similarity": 0.85, "relationship": "synonym"},
    {"tag": "similar_tag2", "similarity": 0.70, "relationship": "related_concept"}
]
"""
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Find tags similar to: {tag}"}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content.strip()
            similar_tags = json.loads(result_text)
            
            return similar_tags[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar tags: {str(e)}")
            return []
    
    async def health_check(self) -> bool:
        """Check if OpenAI tagging service is healthy"""
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": "Health check"}
                ],
                max_tokens=10
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI tagging service health check failed: {str(e)}")
            return False