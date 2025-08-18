"""Profile service implementation for user profile management"""

import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...application.services.profile_service import IProfileService
from ...infrastructure.database.models import UserModel
from ...application.dtos.profile_dtos import (
    UserProfileRequest, 
    UserProfileResponse, 
    TherapyContextRequest, 
    TherapyContextResponse,
    ProfileStatusResponse,
    EmergencyContact,
    MedicalInfo,
    TherapyPreferences
)
from ...infrastructure.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ProfileService(IProfileService):
    """Profile service implementation"""
    
    def __init__(self, database_connection: DatabaseConnection):
        self.database = database_connection
    
    async def get_user_profile(self, user_id: UUID) -> Optional[UserProfileResponse]:
        """Get user profile by ID"""
        try:
            async with self.database.get_session() as session:
                query = select(UserModel).where(UserModel.id == user_id)
                result = await session.execute(query)
                user = result.scalars().first()
                
                if not user:
                    return None
                
                return self._build_profile_response(user)
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def create_or_update_profile(self, user_id: UUID, profile_data: UserProfileRequest) -> UserProfileResponse:
        """Create or update user profile"""
        try:
            async with self.database.get_session() as session:
                # Check if user exists
                query = select(UserModel).where(UserModel.id == user_id)
                result = await session.execute(query)
                user = result.scalars().first()
                
                if not user:
                    raise ValueError(f"User {user_id} not found")
                
                # Update user fields
                update_data = {}
                
                if profile_data.first_name is not None:
                    update_data['first_name'] = profile_data.first_name
                if profile_data.last_name is not None:
                    update_data['last_name'] = profile_data.last_name
                if profile_data.username is not None:
                    update_data['username'] = profile_data.username
                if profile_data.date_of_birth is not None:
                    update_data['date_of_birth'] = profile_data.date_of_birth
                if profile_data.phone_number is not None:
                    update_data['phone_number'] = profile_data.phone_number
                if profile_data.address is not None:
                    update_data['address'] = profile_data.address
                if profile_data.occupation is not None:
                    update_data['occupation'] = profile_data.occupation
                if profile_data.emergency_contact is not None:
                    update_data['emergency_contact'] = profile_data.emergency_contact.dict()
                if profile_data.medical_info is not None:
                    # Map nested medical info to separate columns for backward compatibility
                    if profile_data.medical_info.conditions:
                        update_data['medical_conditions'] = profile_data.medical_info.conditions
                    if profile_data.medical_info.medications:
                        update_data['medications'] = profile_data.medical_info.medications
                    # Note: allergies field not supported in current DB schema
                if profile_data.therapy_preferences is not None:
                    update_data['therapy_preferences'] = profile_data.therapy_preferences.dict()
                if profile_data.user_profile_data is not None:
                    update_data['user_profile_data'] = profile_data.user_profile_data
                
                # Add timestamp
                update_data['updated_at'] = datetime.utcnow()
                
                # Update user
                stmt = update(UserModel).where(UserModel.id == user_id).values(**update_data)
                await session.execute(stmt)
                await session.commit()
                
                # Get updated user
                result = await session.execute(query)
                updated_user = result.scalars().first()
                
                return self._build_profile_response(updated_user)
                
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            raise
    
    async def get_profile_status(self, user_id: UUID) -> ProfileStatusResponse:
        """Get profile completion status"""
        try:
            profile = await self.get_user_profile(user_id)
            if not profile:
                return ProfileStatusResponse(
                    has_profile=False,
                    profile_completeness=0.0,
                    missing_fields=[],
                    last_updated=None
                )
            
            # Calculate completeness - only check fields that exist in current DB schema
            required_fields = ['first_name', 'last_name']  # Only fields that exist
            filled_fields = 0
            missing_fields = []
            
            for field in required_fields:
                if hasattr(profile, field) and getattr(profile, field):
                    filled_fields += 1
                else:
                    missing_fields.append(field)
            
            completeness = (filled_fields / len(required_fields)) * 100
            
            return ProfileStatusResponse(
                has_profile=True,
                profile_completeness=completeness,
                missing_fields=missing_fields,
                last_updated=profile.updated_at
            )
            
        except Exception as e:
            logger.error(f"Error getting profile status: {e}")
            return ProfileStatusResponse(
                has_profile=False,
                profile_completeness=0.0,
                missing_fields=[],
                last_updated=None
            )
    
    async def get_therapy_context(self, user_id: UUID) -> Optional[TherapyContextResponse]:
        """Get therapy context and AI insights"""
        try:
            async with self.database.get_session() as session:
                query = select(UserModel).where(UserModel.id == user_id)
                result = await session.execute(query)
                user = result.scalars().first()
                
                if not user:
                    return None
                
                # Build context summary
                context_summary = self._build_context_summary(user)
                
                return TherapyContextResponse(
                    therapy_context=None,  # Column doesn't exist in current DB
                    ai_insights=None,  # Column doesn't exist in current DB
                    therapy_preferences=None,  # Column doesn't exist in current DB
                    last_updated=user.updated_at,
                    context_summary=context_summary
                )
                
        except Exception as e:
            logger.error(f"Error getting therapy context: {e}")
            return None
    
    async def update_therapy_context(self, user_id: UUID, context_data: TherapyContextRequest) -> TherapyContextResponse:
        """Update therapy context and AI insights"""
        try:
            async with self.database.get_session() as session:
                update_data = {'updated_at': datetime.utcnow()}
                
                # Note: These columns don't exist in current DB schema
                # if context_data.therapy_context is not None:
                #     update_data['therapy_context'] = context_data.therapy_context
                # if context_data.ai_insights is not None:
                #     update_data['ai_insights'] = context_data.ai_insights
                # if context_data.therapy_preferences is not None:
                #     update_data['therapy_preferences'] = context_data.therapy_preferences.dict()
                
                stmt = update(UserModel).where(UserModel.id == user_id).values(**update_data)
                await session.execute(stmt)
                await session.commit()
                
                # Get updated user
                query = select(UserModel).where(UserModel.id == user_id)
                result = await session.execute(query)
                updated_user = result.scalars().first()
                
                context_summary = self._build_context_summary(updated_user)
                
                return TherapyContextResponse(
                    therapy_context=None,  # Column doesn't exist in current DB
                    ai_insights=None,  # Column doesn't exist in current DB
                    therapy_preferences=None,  # Column doesn't exist in current DB
                    last_updated=updated_user.updated_at,
                    context_summary=context_summary
                )
                
        except Exception as e:
            logger.error(f"Error updating therapy context: {e}")
            raise
    
    async def clear_therapy_context(self, user_id: UUID) -> bool:
        """Clear therapy context and AI insights"""
        try:
            async with self.database.get_session() as session:
                # Note: These columns don't exist in current DB schema
                # stmt = update(UserModel).where(UserModel.id == user_id).values(
                #     therapy_context=None,
                #     ai_insights=None,
                #     updated_at=datetime.utcnow()
                # )
                # For now, just update the timestamp since the columns don't exist
                stmt = update(UserModel).where(UserModel.id == user_id).values(
                    updated_at=datetime.utcnow()
                )
                await session.execute(stmt)
                await session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error clearing therapy context: {e}")
            return False
    
    async def generate_ai_insights(self, user_id: UUID) -> Optional[dict]:
        """Generate new AI insights based on user data"""
        try:
            # This would integrate with the AI service to generate insights
            # For now, return a placeholder
            return {
                "mood_patterns": "Based on your emotional records, you tend to feel more anxious in the evenings",
                "stress_triggers": "Work-related stress appears frequently in your notes",
                "coping_strategies": "Breathing exercises seem to help you most when feeling overwhelmed",
                "progress_areas": "You've shown improvement in managing daily stress levels"
            }
        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return None
    
    def _build_profile_response(self, user: UserModel) -> UserProfileResponse:
        """Build profile response from user model"""
        # Since extended profile columns don't exist in current DB, set them to None
        # Parse emergency contact
        emergency_contact = None
        # if user.emergency_contact:  # Column doesn't exist
        #     try:
        #         emergency_contact = EmergencyContact(**user.emergency_contact)
        #     except Exception:
        #         logger.warning(f"Invalid emergency contact data for user {user.id}")
        
        # Parse medical info - columns don't exist in current DB
        medical_info = None
        # if user.medical_conditions or user.medications:  # Columns don't exist
        #     # Handle both list and string formats for backward compatibility
        #     conditions = user.medical_conditions or []
        #     if isinstance(conditions, str):
        #         conditions = [conditions] if conditions else []
        #     elif not isinstance(conditions, list):
        #         conditions = []
        #         
        #     medications = user.medications or []
        #     if isinstance(medications, str):
        #         medications = [medications] if medications else []
        #     elif not isinstance(medications, list):
        #         medications = []
        #         
        #     medical_info = MedicalInfo(
        #         conditions=conditions,
        #         medications=medications,
        #         allergies=[]  # No allergies field in current DB schema
        #     )
        
        # Parse therapy preferences - column doesn't exist in current DB
        therapy_preferences = None
        # if user.therapy_preferences:  # Column doesn't exist
        #     try:
        #         therapy_preferences = TherapyPreferences(**user.therapy_preferences)
        #     except Exception:
        #         logger.warning(f"Invalid therapy preferences data for user {user.id}")
        
        # Calculate profile completeness based on available fields only
        required_fields = ['first_name', 'last_name']  # Only fields that exist
        filled_fields = 0
        for field in required_fields:
            if getattr(user, field):
                filled_fields += 1
            
        is_complete = filled_fields >= 2  # At least 2 out of 2 required fields
        
        return UserProfileResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            date_of_birth=user.date_of_birth,
            phone_number=None,  # Column doesn't exist
            address=None,  # Column doesn't exist
            occupation=None,  # Column doesn't exist
            emergency_contact=emergency_contact,
            medical_info=medical_info,
            therapy_preferences=therapy_preferences,
            is_profile_complete=is_complete,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
    
    def _build_context_summary(self, user: UserModel) -> Optional[str]:
        """Build human-readable context summary"""
        # Since therapy_context and ai_insights columns don't exist in current DB, return None
        return None
        
        # Original code commented out since columns don't exist:
        # if not user.therapy_context and not user.ai_insights:
        #     return None
        # 
        # summary_parts = []
        # 
        # if user.therapy_context:
        #     if isinstance(user.therapy_context, dict):
        #         if 'mood_patterns' in user.therapy_context:
        #             summary_parts.append(f"Mood patterns: {user.therapy_context['mood_patterns']}")
        #         if 'stress_triggers' in user.therapy_context:
        #             summary_parts.append(f"Stress triggers: {user.therapy_context['stress_triggers']}")
        # 
        # if user.ai_insights:
        #     if isinstance(user.ai_insights, dict):
        #         if 'progress_areas' in user.ai_insights:
        #             summary_parts.append(f"Progress areas: {user.ai_insights['progress_areas']}")
        #         if 'coping_strategies' in user.ai_insights:
        #             summary_parts.append(f"Effective coping: {user.ai_insights['coping_strategies']}")
        # 
        # return " | ".join(summary_parts) if summary_parts else None
