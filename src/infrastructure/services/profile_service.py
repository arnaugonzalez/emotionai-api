"""Profile service implementation for user profile management"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, update, insert
from sqlalchemy.ext.asyncio import AsyncSession

from ...application.services.profile_service import IProfileService
from ...infrastructure.database.models import UserModel, UserProfileDataModel, AgentPersonalityModel
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
                # Get user and related profile data
                query = select(UserModel, UserProfileDataModel).outerjoin(
                    UserProfileDataModel, UserModel.id == UserProfileDataModel.user_id
                ).where(UserModel.id == user_id)
                
                result = await session.execute(query)
                row = result.first()
                
                if not row:
                    return None
                
                user, profile_data = row
                return self._build_profile_response(user, profile_data)
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return None
    
    async def create_or_update_profile(self, user_id: UUID, profile_data: UserProfileRequest) -> UserProfileResponse:
        """Create or update user profile"""
        try:
            async with self.database.get_session() as session:
                # Check if user exists
                user_query = select(UserModel).where(UserModel.id == user_id)
                user_result = await session.execute(user_query)
                user = user_result.scalars().first()
                
                if not user:
                    raise ValueError(f"User {user_id} not found")
                
                # Update user fields
                user_update_data = {}
                
                if profile_data.first_name is not None:
                    user_update_data['first_name'] = profile_data.first_name
                if profile_data.last_name is not None:
                    user_update_data['last_name'] = profile_data.last_name
                if profile_data.username is not None:
                    user_update_data['username'] = profile_data.username
                if profile_data.date_of_birth is not None:
                    user_update_data['date_of_birth'] = profile_data.date_of_birth
                if profile_data.phone_number is not None:
                    user_update_data['phone_number'] = profile_data.phone_number
                if profile_data.address is not None:
                    user_update_data['address'] = profile_data.address
                if profile_data.occupation is not None:
                    user_update_data['occupation'] = profile_data.occupation
                if profile_data.emergency_contact is not None:
                    user_update_data['emergency_contact'] = profile_data.emergency_contact.dict()
                if profile_data.medical_info is not None:
                    # Map nested medical info to separate columns for backward compatibility
                    if profile_data.medical_info.conditions:
                        user_update_data['medical_conditions'] = profile_data.medical_info.conditions
                    if profile_data.medical_info.medications:
                        user_update_data['medications'] = profile_data.medical_info.medications
                if profile_data.therapy_preferences is not None:
                    user_update_data['therapy_preferences'] = profile_data.therapy_preferences.dict()
                if profile_data.terms_accepted is not None:
                    user_update_data['terms_accepted'] = bool(profile_data.terms_accepted)
                    if bool(profile_data.terms_accepted):
                        user_update_data['terms_accepted_at'] = datetime.now(timezone.utc)
                
                # Add timestamp
                user_update_data['updated_at'] = datetime.now(timezone.utc)
                
                # Update user
                if user_update_data:
                    stmt = update(UserModel).where(UserModel.id == user_id).values(**user_update_data)
                    await session.execute(stmt)
                
                # Handle profile data in separate table
                if profile_data.user_profile_data:
                    await self._upsert_profile_data(session, user_id, profile_data.user_profile_data)
                
                # Commit all changes
                await session.commit()
                
                # Get updated user and profile data
                updated_query = select(UserModel, UserProfileDataModel).outerjoin(
                    UserProfileDataModel, UserModel.id == UserProfileDataModel.user_id
                ).where(UserModel.id == user_id)
                
                updated_result = await session.execute(updated_query)
                updated_row = updated_result.first()
                
                return self._build_profile_response(updated_row[0], updated_row[1])
                
        except Exception as e:
            logger.error(f"Error updating user profile: {e}")
            raise
    
    async def _upsert_profile_data(self, session: AsyncSession, user_id: UUID, profile_data: dict):
        """Upsert profile data in the separate table"""
        try:
            # Check if profile data exists
            existing_query = select(UserProfileDataModel).where(UserProfileDataModel.user_id == user_id)
            existing_result = await session.execute(existing_query)
            existing_profile = existing_result.scalars().first()
            
            profile_update_data = {
                'personality_type': profile_data.get('personality_type'),
                'relaxation_time': profile_data.get('relaxation_time'),
                'selfcare_frequency': profile_data.get('selfcare_frequency'),
                'relaxation_tools': profile_data.get('relaxation_tools'),
                'has_previous_mental_health_app_experience': profile_data.get('has_previous_mental_health_app_experience'),
                'therapy_chat_history_preference': profile_data.get('therapy_chat_history_preference'),
                'country': profile_data.get('country'),
                'gender': profile_data.get('gender'),
                'updated_at': datetime.now(timezone.utc)
            }
            
            if existing_profile:
                # Update existing
                stmt = update(UserProfileDataModel).where(
                    UserProfileDataModel.user_id == user_id
                ).values(**profile_update_data)
                await session.execute(stmt)
            else:
                # Insert new
                profile_update_data['user_id'] = user_id
                profile_update_data['created_at'] = datetime.now(timezone.utc)
                
                stmt = insert(UserProfileDataModel).values(**profile_update_data)
                await session.execute(stmt)
                
        except Exception as e:
            logger.error(f"Error upserting profile data: {e}")
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
            
            # Calculate completeness based on available fields
            required_fields = ['first_name', 'last_name', 'phone_number']
            filled_fields = 0
            missing_fields = []
            
            for field in required_fields:
                if hasattr(profile, field) and getattr(profile, field):
                    filled_fields += 1
                else:
                    missing_fields.append(field)
            
            # Check if profile data exists
            if profile.user_profile_data:
                filled_fields += 1
            else:
                missing_fields.append('profile_preferences')
            
            completeness = (filled_fields / (len(required_fields) + 1)) * 100
            
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
                # Get user and agent personality data
                query = select(UserModel, AgentPersonalityModel).outerjoin(
                    AgentPersonalityModel, UserModel.id == AgentPersonalityModel.user_id
                ).where(UserModel.id == user_id)
                
                result = await session.execute(query)
                row = result.first()
                
                if not row:
                    return None
                
                user, agent_personality = row
                context_summary = self._build_context_summary(user, agent_personality)
                
                return TherapyContextResponse(
                    therapy_context=user.therapy_context,
                    ai_insights=user.ai_insights,
                    therapy_preferences=user.therapy_preferences,
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
                update_data = {'updated_at': datetime.now(timezone.utc)}
                
                if context_data.therapy_context is not None:
                    update_data['therapy_context'] = context_data.therapy_context
                if context_data.ai_insights is not None:
                    update_data['ai_insights'] = context_data.ai_insights
                if context_data.therapy_preferences is not None:
                    update_data['therapy_preferences'] = context_data.therapy_preferences.dict()
                
                stmt = update(UserModel).where(UserModel.id == user_id).values(**update_data)
                await session.execute(stmt)
                await session.commit()
                
                # Get updated user
                query = select(UserModel, AgentPersonalityModel).outerjoin(
                    AgentPersonalityModel, UserModel.id == AgentPersonalityModel.user_id
                ).where(UserModel.id == user_id)
                
                result = await session.execute(query)
                updated_row = result.first()
                
                context_summary = self._build_context_summary(updated_row[0], updated_row[1])
                
                return TherapyContextResponse(
                    therapy_context=updated_row[0].therapy_context,
                    ai_insights=updated_row[0].ai_insights,
                    therapy_preferences=updated_row[0].therapy_preferences,
                    last_updated=updated_row[0].updated_at,
                    context_summary=context_summary
                )
                
        except Exception as e:
            logger.error(f"Error updating therapy context: {e}")
            raise
    
    async def clear_therapy_context(self, user_id: UUID) -> bool:
        """Clear therapy context and AI insights"""
        try:
            async with self.database.get_session() as session:
                stmt = update(UserModel).where(UserModel.id == user_id).values(
                    therapy_context=None,
                    ai_insights=None,
                    updated_at=datetime.now(timezone.utc)
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
    
    def _build_profile_response(self, user: UserModel, profile_data: Optional[UserProfileDataModel] = None) -> UserProfileResponse:
        """Build profile response from user model and profile data"""
        # Parse emergency contact
        emergency_contact = None
        if user.emergency_contact:
            try:
                emergency_contact = EmergencyContact(**user.emergency_contact)
            except Exception:
                logger.warning(f"Invalid emergency contact data for user {user.id}")
        
        # Parse medical info - map from separate columns to nested structure
        medical_info = None
        if user.medical_conditions or user.medications:
            # Handle both list and string formats for backward compatibility
            conditions = user.medical_conditions or []
            if isinstance(conditions, str):
                conditions = [conditions] if conditions else []
            elif not isinstance(conditions, list):
                conditions = []
                
            medications = user.medications or []
            if isinstance(medications, str):
                medications = [medications] if medications else []
            elif not isinstance(medications, list):
                medications = []
                
            medical_info = MedicalInfo(
                conditions=conditions,
                medications=medications,
                allergies=[]  # No allergies field in current DB schema
            )
        
        # Parse therapy preferences
        therapy_preferences = None
        if user.therapy_preferences:
            try:
                therapy_preferences = TherapyPreferences(**user.therapy_preferences)
            except Exception:
                logger.warning(f"Invalid therapy preferences data for user {user.id}")
        
        # Build user profile data - prioritize new table over legacy JSON
        user_profile_data = None
        if profile_data:
            # Use data from new separate table
            user_profile_data = {
                'personality_type': profile_data.personality_type,
                'relaxation_time': profile_data.relaxation_time,
                'selfcare_frequency': profile_data.selfcare_frequency,
                'relaxation_tools': profile_data.relaxation_tools or [],
                'has_previous_mental_health_app_experience': profile_data.has_previous_mental_health_app_experience,
                'therapy_chat_history_preference': profile_data.therapy_chat_history_preference,
                'country': profile_data.country,
                'gender': profile_data.gender,
            }
        elif user.user_profile_data:
            # Fallback to legacy JSON column if new table doesn't exist yet
            try:
                if isinstance(user.user_profile_data, dict):
                    user_profile_data = user.user_profile_data
                else:
                    logger.warning(f"Invalid user_profile_data format for user {user.id}")
            except Exception:
                logger.warning(f"Error parsing legacy user_profile_data for user {user.id}")
        
        # Calculate profile completeness based on available fields
        required_fields = ['first_name', 'last_name', 'phone_number']
        filled_fields = 0
        for field in required_fields:
            if getattr(user, field):
                filled_fields += 1
        
        # Check if emergency contact exists
        if user.emergency_contact:
            filled_fields += 1
            
        # Check if profile preferences exist
        if user_profile_data:
            filled_fields += 1
            
        is_complete = filled_fields >= 3  # At least 3 out of 5 required fields
        
        return UserProfileResponse(
            id=str(user.id),
            email=user.email,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            date_of_birth=user.date_of_birth,
            phone_number=user.phone_number,
            address=user.address,
            occupation=user.occupation,
            emergency_contact=emergency_contact,
            medical_info=medical_info,
            therapy_preferences=therapy_preferences,
            user_profile_data=user_profile_data,
            is_profile_complete=is_complete,
            created_at=user.created_at,
            updated_at=user.updated_at
            ,terms_accepted=user.terms_accepted
        )
    
    def _build_context_summary(self, user: UserModel, agent_personality: Optional[AgentPersonalityModel] = None) -> Optional[str]:
        """Build human-readable context summary"""
        summary_parts = []
        
        if user.therapy_context:
            if isinstance(user.therapy_context, dict):
                if 'mood_patterns' in user.therapy_context:
                    summary_parts.append(f"Mood patterns: {user.therapy_context['mood_patterns']}")
                if 'stress_triggers' in user.therapy_context:
                    summary_parts.append(f"Stress triggers: {user.therapy_context['stress_triggers']}")
        
        if user.ai_insights:
            if isinstance(user.ai_insights, dict):
                if 'progress_areas' in user.ai_insights:
                    summary_parts.append(f"Progress areas: {user.ai_insights['progress_areas']}")
                if 'coping_strategies' in user.ai_insights:
                    summary_parts.append(f"Effective coping: {user.ai_insights['coping_strategies']}")
        
        # Check new agent personality table first
        if agent_personality:
            if agent_personality.mood_patterns:
                summary_parts.append(f"Stored mood patterns: {agent_personality.mood_patterns}")
            if agent_personality.stress_triggers:
                summary_parts.append(f"Stored stress triggers: {agent_personality.stress_triggers}")
            if agent_personality.coping_strategies:
                summary_parts.append(f"Stored coping strategies: {agent_personality.coping_strategies}")
        # Fallback to legacy JSON column if new table doesn't exist yet
        elif user.agent_personality_data:
            try:
                if isinstance(user.agent_personality_data, dict):
                    if 'mood_patterns' in user.agent_personality_data:
                        summary_parts.append(f"Legacy mood patterns: {user.agent_personality_data['mood_patterns']}")
                    if 'stress_triggers' in user.agent_personality_data:
                        summary_parts.append(f"Legacy stress triggers: {user.agent_personality_data['stress_triggers']}")
                    if 'coping_strategies' in user.agent_personality_data:
                        summary_parts.append(f"Legacy coping strategies: {user.agent_personality_data['coping_strategies']}")
            except Exception:
                logger.warning(f"Error parsing legacy agent_personality_data for user {user.id}")
        
        return " | ".join(summary_parts) if summary_parts else None
