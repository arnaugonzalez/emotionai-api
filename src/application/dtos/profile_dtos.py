"""Profile DTOs for user profile management and therapy context"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr


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
    communication_style: Optional[str] = Field(None, description="Preferred communication style")
    session_frequency: Optional[str] = Field(None, description="Preferred session frequency")
    focus_areas: List[str] = Field(default_factory=list, description="Areas of focus")
    goals: Optional[str] = Field(None, description="Therapy goals")


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


class UserProfileResponse(BaseModel):
    """User profile response"""
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
