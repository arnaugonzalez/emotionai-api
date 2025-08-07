"""
Value Object: Agent Personality

Represents the different personality types available for AI agents.
Value objects are immutable and represent domain concepts.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any


class AgentPersonality(Enum):
    """Enumeration of available agent personalities"""
    
    EMPATHETIC_SUPPORTIVE = "empathetic_supportive"
    ENCOURAGING_MOTIVATIONAL = "encouraging_motivational"
    ANALYTICAL_PRACTICAL = "analytical_practical"
    MINDFUL_CONTEMPLATIVE = "mindful_contemplative"
    CREATIVE_EXPRESSIVE = "creative_expressive"
    
    def get_description(self) -> str:
        """Get human-readable description of the personality"""
        descriptions = {
            self.EMPATHETIC_SUPPORTIVE: "Warm, validating responses with deep empathy",
            self.ENCOURAGING_MOTIVATIONAL: "Positive, strength-focused with motivation",
            self.ANALYTICAL_PRACTICAL: "Structured, solution-oriented approaches",
            self.MINDFUL_CONTEMPLATIVE: "Present-moment awareness and mindfulness",
            self.CREATIVE_EXPRESSIVE: "Artistic and creative approaches to healing"
        }
        return descriptions.get(self, "Unknown personality")
    
    def get_system_prompt_addition(self) -> str:
        """Get the system prompt addition for this personality"""
        prompt_additions = {
            self.EMPATHETIC_SUPPORTIVE: 
                "Focus on emotional validation and gentle support. Use phrases like 'I hear you' and 'That sounds really difficult.'",
            self.ENCOURAGING_MOTIVATIONAL: 
                "Emphasize resilience and growth. Highlight user strengths and past successes.",
            self.ANALYTICAL_PRACTICAL: 
                "Offer structured approaches and concrete strategies. Help break down problems into manageable steps.",
            self.MINDFUL_CONTEMPLATIVE: 
                "Encourage present-moment awareness and self-reflection. Suggest mindfulness techniques.",
            self.CREATIVE_EXPRESSIVE: 
                "Suggest creative outlets for emotional expression. Encourage journaling, art, or other creative activities."
        }
        return prompt_additions.get(self, "")
    
    def get_default_preferences(self) -> Dict[str, Any]:
        """Get default agent preferences for this personality"""
        preferences = {
            self.EMPATHETIC_SUPPORTIVE: {
                "response_tone": "warm",
                "validation_frequency": "high",
                "suggestion_style": "gentle"
            },
            self.ENCOURAGING_MOTIVATIONAL: {
                "response_tone": "upbeat",
                "validation_frequency": "medium",
                "suggestion_style": "motivational"
            },
            self.ANALYTICAL_PRACTICAL: {
                "response_tone": "neutral",
                "validation_frequency": "medium",
                "suggestion_style": "structured"
            },
            self.MINDFUL_CONTEMPLATIVE: {
                "response_tone": "calm",
                "validation_frequency": "high",
                "suggestion_style": "reflective"
            },
            self.CREATIVE_EXPRESSIVE: {
                "response_tone": "inspiring",
                "validation_frequency": "medium",
                "suggestion_style": "creative"
            }
        }
        return preferences.get(self, {})
    
    @classmethod
    def from_string(cls, value: str) -> 'AgentPersonality':
        """Create personality from string value"""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.EMPATHETIC_SUPPORTIVE  # Default fallback
    
    @classmethod
    def get_all_descriptions(cls) -> Dict[str, str]:
        """Get all personalities with their descriptions"""
        return {
            personality.value: personality.get_description()
            for personality in cls
        } 