"""
Value Object: User Profile

Represents user profile information as an immutable value object.
Contains validation and business logic for profile completeness.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass(frozen=True)
class UserProfile:
    """Immutable user profile value object"""
    
    # Basic demographic information (from frontend form)
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    occupation: Optional[str] = None
    country: Optional[str] = None
    personality_type: Optional[str] = None
    relaxation_time: Optional[str] = None
    selfcare_frequency: Optional[str] = None
    relaxation_tools: List[str] = field(default_factory=list)
    has_previous_mental_health_app_experience: Optional[bool] = None
    therapy_chat_history_preference: Optional[str] = None
    
    # Therapy and wellness focused fields
    goals: List[str] = field(default_factory=list)
    concerns: List[str] = field(default_factory=list)
    preferred_activities: List[str] = field(default_factory=list)
    therapy_goals: List[str] = field(default_factory=list)
    wellness_goals: List[str] = field(default_factory=list)
    coping_strategies: List[str] = field(default_factory=list)
    mindfulness_practices: List[str] = field(default_factory=list)
    communication_style: Optional[str] = None
    timezone: Optional[str] = None
    preferred_session_length: Optional[int] = None  # in minutes
    crisis_contacts: List[Dict[str, str]] = field(default_factory=list)
    
    def is_complete(self) -> bool:
        """Check if profile has minimum required information for personalization"""
        basic_info_complete = self.name and self.age and self.gender
        goals_complete = (
            len(self.goals) > 0 or 
            len(self.therapy_goals) > 0 or 
            len(self.wellness_goals) > 0
        )
        context_complete = (
            len(self.concerns) > 0 or 
            len(self.preferred_activities) > 0 or
            len(self.relaxation_tools) > 0
        )
        return basic_info_complete and (goals_complete or context_complete)
    
    def get_completeness_score(self) -> float:
        """Get profile completeness as a percentage (0.0 to 1.0)"""
        total_fields = 12  # Number of key profile areas (basic + therapy)
        completed_fields = 0
        
        # Basic demographic fields
        if self.name:
            completed_fields += 1
        if self.age:
            completed_fields += 1
        if self.gender:
            completed_fields += 1
        if self.occupation:
            completed_fields += 1
        if self.personality_type:
            completed_fields += 1
            
        # Therapy and wellness fields
        if self.goals:
            completed_fields += 1
        if self.concerns:
            completed_fields += 1
        if self.preferred_activities or self.relaxation_tools:
            completed_fields += 1
        if self.therapy_goals:
            completed_fields += 1
        if self.wellness_goals:
            completed_fields += 1
        if self.coping_strategies:
            completed_fields += 1
        if self.mindfulness_practices:
            completed_fields += 1
            
        return completed_fields / total_fields
    
    def get_missing_fields(self) -> List[str]:
        """Get list of profile fields that are empty"""
        missing = []
        
        # Basic demographic fields
        if not self.name:
            missing.append("name")
        if not self.age:
            missing.append("age")
        if not self.gender:
            missing.append("gender")
        if not self.occupation:
            missing.append("occupation")
        if not self.personality_type:
            missing.append("personality_type")
            
        # Therapy and wellness fields
        if not self.goals:
            missing.append("general_goals")
        if not self.concerns:
            missing.append("concerns")
        if not self.preferred_activities and not self.relaxation_tools:
            missing.append("preferred_activities")
        if not self.therapy_goals:
            missing.append("therapy_goals")
        if not self.wellness_goals:
            missing.append("wellness_goals")
        if not self.coping_strategies:
            missing.append("coping_strategies")
        if not self.mindfulness_practices:
            missing.append("mindfulness_practices")
            
        return missing
    
    def get_all_goals(self) -> List[str]:
        """Get all goals combined from different categories"""
        return self.goals + self.therapy_goals + self.wellness_goals
    
    def has_crisis_support(self) -> bool:
        """Check if user has crisis contact information"""
        return len(self.crisis_contacts) > 0
    
    def get_personalization_context(self) -> Dict[str, Any]:
        """Get context data for agent personalization"""
        return {
            # Basic user context
            "name": self.name,
            "age": self.age,
            "personality_type": self.personality_type,
            "relaxation_time": self.relaxation_time,
            "selfcare_frequency": self.selfcare_frequency,
            "relaxation_tools": self.relaxation_tools,
            "has_mental_health_app_experience": self.has_previous_mental_health_app_experience,
            # Therapy and wellness context
            "goals": self.get_all_goals(),
            "concerns": self.concerns,
            "preferred_activities": self.preferred_activities,
            "coping_strategies": self.coping_strategies,
            "mindfulness_practices": self.mindfulness_practices,
            "communication_style": self.communication_style,
            "therapy_chat_history_preference": self.therapy_chat_history_preference,
            # Metadata
            "completeness_score": self.get_completeness_score(),
            "has_crisis_support": self.has_crisis_support()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create UserProfile from dictionary data"""
        return cls(
            # Basic demographic fields
            name=data.get("name"),
            age=data.get("age"),
            gender=data.get("gender"),
            occupation=data.get("occupation"),
            country=data.get("country"),
            personality_type=data.get("personality_type"),
            relaxation_time=data.get("relaxation_time"),
            selfcare_frequency=data.get("selfcare_frequency"),
            relaxation_tools=data.get("relaxation_tools", []),
            has_previous_mental_health_app_experience=data.get("has_previous_mental_health_app_experience"),
            therapy_chat_history_preference=data.get("therapy_chat_history_preference"),
            # Therapy and wellness fields
            goals=data.get("goals", []),
            concerns=data.get("concerns", []),
            preferred_activities=data.get("preferred_activities", []),
            therapy_goals=data.get("therapy_goals", []),
            wellness_goals=data.get("wellness_goals", []),
            coping_strategies=data.get("coping_strategies", []),
            mindfulness_practices=data.get("mindfulness_practices", []),
            communication_style=data.get("communication_style"),
            timezone=data.get("timezone"),
            preferred_session_length=data.get("preferred_session_length"),
            crisis_contacts=data.get("crisis_contacts", [])
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert UserProfile to dictionary"""
        return {
            # Basic demographic fields
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "occupation": self.occupation,
            "country": self.country,
            "personality_type": self.personality_type,
            "relaxation_time": self.relaxation_time,
            "selfcare_frequency": self.selfcare_frequency,
            "relaxation_tools": self.relaxation_tools,
            "has_previous_mental_health_app_experience": self.has_previous_mental_health_app_experience,
            "therapy_chat_history_preference": self.therapy_chat_history_preference,
            # Therapy and wellness fields
            "goals": self.goals,
            "concerns": self.concerns,
            "preferred_activities": self.preferred_activities,
            "therapy_goals": self.therapy_goals,
            "wellness_goals": self.wellness_goals,
            "coping_strategies": self.coping_strategies,
            "mindfulness_practices": self.mindfulness_practices,
            "communication_style": self.communication_style,
            "timezone": self.timezone,
            "preferred_session_length": self.preferred_session_length,
            "crisis_contacts": self.crisis_contacts
        }
    
    def update(self, **kwargs) -> 'UserProfile':
        """Create new UserProfile with updated fields (immutable update)"""
        current_data = self.to_dict()
        current_data.update(kwargs)
        return self.from_dict(current_data) 