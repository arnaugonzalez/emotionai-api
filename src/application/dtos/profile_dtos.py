"""Profile DTOs for user profile management and therapy context"""

from datetime import datetime
from typing import ClassVar, Optional, Dict, Any, List, Self
from pydantic import BaseModel, Field, EmailStr, field_validator, model_validator, ConfigDict


class EmergencyContact(BaseModel):
    """Emergency contact information"""
    name: str = Field(..., description="Contact person name")
    relationship: str = Field(..., description="Relationship to user")
    phone: str = Field(..., description="Phone number")
    email: Optional[EmailStr] = Field(None, description="Email address")


class MedicalInfo(BaseModel):
    """Medical information"""
    conditions: List[str] = Field(default_factory=list, description="Medical conditions")
    medications: List[str] = Field(default_factory=list, description="Current medications")
    allergies: List[str] = Field(default_factory=list, description="Known allergies")


class TherapyPreferences(BaseModel):
    """User's therapy preferences"""
    ALLOWED_COMMUNICATION_STYLES: ClassVar[List[str]] = [
        "supportive", "direct", "analytical", "casual", "formal"
    ]

    communication_style: Optional[str] = Field(None, description="Preferred communication style")
    session_frequency: Optional[str] = Field(None, description="Preferred session frequency")
    focus_areas: List[str] = Field(default_factory=list, description="Areas of focus")
    goals: Optional[str] = Field(None, description="Therapy goals")

    @field_validator("communication_style")
    @classmethod
    def validate_communication_style(cls, v: Optional[str]) -> Optional[str]:
        allowed = ["supportive", "direct", "analytical", "casual", "formal"]
        if v is not None and v not in allowed:
            raise ValueError(f"communication_style must be one of: {allowed}")
        return v


class UserProfileRequest(BaseModel):
    """Request to create/update user profile"""
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    username: Optional[str] = Field(None, description="Username")
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")
    phone_number: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Address")
    occupation: Optional[str] = Field(None, description="Occupation")
    emergency_contact: Optional[EmergencyContact] = Field(None, description="Emergency contact")
    medical_info: Optional[MedicalInfo] = Field(None, description="Medical information")
    therapy_preferences: Optional[TherapyPreferences] = Field(None, description="Therapy preferences")
    user_profile_data: Optional[Dict[str, Any]] = Field(None, description="Additional profile data (personality type, preferences, etc.)")
    terms_accepted: Optional[bool] = Field(None, description="Whether user accepted terms")

    @model_validator(mode='after')
    def at_least_one_field_provided(self) -> Self:
        fields_to_check = [
            'first_name', 'last_name', 'username', 'date_of_birth',
            'phone_number', 'address', 'occupation', 'emergency_contact',
            'medical_info', 'therapy_preferences', 'user_profile_data', 'terms_accepted'
        ]
        if all(getattr(self, f) is None for f in fields_to_check):
            raise ValueError("At least one profile field must be provided")
        return self


class UserProfileResponse(BaseModel):
    """User profile response"""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="User ID")
    email: str = Field(..., description="Email address")
    username: Optional[str] = Field(None, description="Username")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    date_of_birth: Optional[datetime] = Field(None, description="Date of birth")
    phone_number: Optional[str] = Field(None, description="Phone number")
    address: Optional[str] = Field(None, description="Address")
    occupation: Optional[str] = Field(None, description="Occupation")
    emergency_contact: Optional[EmergencyContact] = Field(None, description="Emergency contact")
    medical_info: Optional[MedicalInfo] = Field(None, description="Medical information")
    therapy_preferences: Optional[TherapyPreferences] = Field(None, description="Therapy preferences")
    user_profile_data: Optional[Dict[str, Any]] = Field(None, description="Additional profile data (personality type, preferences, etc.)")
    is_profile_complete: bool = Field(..., description="Whether profile is complete")
    created_at: datetime = Field(..., description="Profile creation date")
    updated_at: datetime = Field(..., description="Profile last update date")
    terms_accepted: Optional[bool] = Field(None, description="Whether user accepted terms")


class TherapyContextRequest(BaseModel):
    """Request to update therapy context"""
    therapy_context: Optional[Dict[str, Any]] = Field(None, description="Therapy context data")
    ai_insights: Optional[Dict[str, Any]] = Field(None, description="AI-generated insights")
    therapy_preferences: Optional[TherapyPreferences] = Field(None, description="Updated therapy preferences")


class TherapyContextResponse(BaseModel):
    """Therapy context response"""
    therapy_context: Optional[Dict[str, Any]] = Field(None, description="What AI knows about the user")
    ai_insights: Optional[Dict[str, Any]] = Field(None, description="AI-generated insights")
    therapy_preferences: Optional[TherapyPreferences] = Field(None, description="User's therapy preferences")
    last_updated: datetime = Field(..., description="Last update timestamp")
    context_summary: Optional[str] = Field(None, description="Human-readable context summary")


class ProfileStatusResponse(BaseModel):
    """Profile status response"""
    has_profile: bool = Field(..., description="Whether user has a profile")
    profile_completeness: float = Field(..., description="Profile completeness percentage (0-100)")
    missing_fields: List[str] = Field(default_factory=list, description="Missing required fields")
    last_updated: Optional[datetime] = Field(None, description="Last profile update")

    @field_validator("profile_completeness")
    @classmethod
    def completeness_in_range(cls, v: float) -> float:
        if not (0 <= v <= 100):
            raise ValueError("profile_completeness must be between 0 and 100")
        return v
