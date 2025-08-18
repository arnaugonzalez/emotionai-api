#!/usr/bin/env python3
"""
Test Data Creation Script for EmotionAI API
Creates realistic sample data for testing the backend functionality
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
import bcrypt

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.infrastructure.config.settings import settings
from src.infrastructure.database.connection import DatabaseConnection
from src.infrastructure.database.models import (
    UserModel,
    EmotionalRecordModel,
    BreathingSessionModel,
    UserProfileModel,
    TagSemanticModel
)

async def create_test_data():
    """Create comprehensive test data for the EmotionAI API"""
    
    print("🧪 Starting test data creation...")
    print(f"📊 Environment: {settings.environment}")
    print(f"🔗 Database URL: {settings.database_url.replace(settings.database_url.split('://')[1].split('@')[0], '***:***')}")
    
    try:
        # Create database connection
        print("\n📡 Connecting to database...")
        db = await DatabaseConnection.create(settings)
        
        async with db.get_session() as session:
            print("👤 Creating test user...")
            
            # Check if test user already exists
            from sqlalchemy import select
            result = await session.execute(
                select(UserModel).where(UserModel.email == "test@emotionai.com")
            )
            existing_user = result.scalar_one_or_none()
            
            if existing_user:
                print("   ⚠️  Test user already exists, using existing user")
                test_user = existing_user
            else:
                # Create test user
                hashed_password = bcrypt.hashpw("testpass123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                test_user = UserModel(
                    email="test@emotionai.com",
                    hashed_password=hashed_password,
                    first_name="Arnau",
                    last_name="Gonzalez",
                    date_of_birth=datetime(1998, 12, 1),
                    is_active=True,
                    is_verified=True,
                    agent_personality_data={
                        "preferred_agent_type": "therapist",
                        "communication_style": "supportive",
                        "interests": ["mindfulness", "stress_management", "personal_growth"]
                    },
                    user_profile_data={
                        "timezone": "America/New_York",
                        "language": "en",
                        "experience_level": "intermediate"
                    },
                    last_login_at=datetime.now() - timedelta(hours=2)
                )
                session.add(test_user)
                await session.flush()  # Get the ID
                print(f"   ✅ Created test user: {test_user.email} (ID: {test_user.id})")
            
            # Create breathing sessions
            print("\n🫁 Creating breathing sessions...")
            breathing_patterns = [
                {
                    "pattern_name": "4-7-8 Breathing",
                    "duration_minutes": 10,
                    "effectiveness_rating": 4,
                    "notes": "Felt very relaxed after this session. Great for evening routine.",
                    "days_ago": 1,
                    "session_data": {
                        "inhale_duration": 4,
                        "hold_duration": 7,
                        "exhale_duration": 8,
                        "cycles_completed": 8
                    },
                    "tags": ["relaxation", "sleep_preparation", "anxiety_relief"]
                },
                {
                    "pattern_name": "Box Breathing",
                    "duration_minutes": 15,
                    "effectiveness_rating": 5,
                    "notes": "Perfect for focus and concentration. Used before important meeting.",
                    "days_ago": 2,
                    "session_data": {
                        "inhale_duration": 4,
                        "hold_duration": 4,
                        "exhale_duration": 4,
                        "hold_empty_duration": 4,
                        "cycles_completed": 15
                    },
                    "tags": ["focus", "concentration", "work_preparation"]
                },
                {
                    "pattern_name": "Belly Breathing",
                    "duration_minutes": 8,
                    "effectiveness_rating": 3,
                    "notes": "Good session but got distracted by phone notifications.",
                    "days_ago": 3,
                    "session_data": {
                        "breathing_type": "diaphragmatic",
                        "cycles_completed": 12,
                        "interruptions": 2
                    },
                    "tags": ["mindfulness", "distraction", "basic_technique"]
                },
                {
                    "pattern_name": "Coherent Breathing",
                    "duration_minutes": 12,
                    "effectiveness_rating": 4,
                    "notes": "Steady rhythm helped with stress from work deadline.",
                    "days_ago": 5,
                    "session_data": {
                        "breaths_per_minute": 5,
                        "total_breaths": 60,
                        "heart_rate_variability": "improved"
                    },
                    "tags": ["stress_relief", "work_stress", "steady_rhythm"]
                },
                {
                    "pattern_name": "4-7-8 Breathing",
                    "duration_minutes": 5,
                    "effectiveness_rating": 2,
                    "notes": "Short session, felt rushed. Need more time for this technique.",
                    "days_ago": 7,
                    "session_data": {
                        "inhale_duration": 4,
                        "hold_duration": 7,
                        "exhale_duration": 8,
                        "cycles_completed": 4
                    },
                    "tags": ["rushed", "incomplete", "time_pressure"]
                }
            ]
            
            for pattern_data in breathing_patterns:
                session_time = datetime.now() - timedelta(days=pattern_data["days_ago"])
                breathing_session = BreathingSessionModel(
                    user_id=test_user.id,
                    pattern_name=pattern_data["pattern_name"],
                    duration_minutes=pattern_data["duration_minutes"],
                    completed=True,
                    effectiveness_rating=pattern_data["effectiveness_rating"],
                    notes=pattern_data["notes"],
                    session_data=pattern_data["session_data"],
                    tags=pattern_data["tags"],
                    tag_confidence=0.9,
                    processed_for_tags=True,
                    started_at=session_time,
                    completed_at=session_time + timedelta(minutes=pattern_data["duration_minutes"])
                )
                session.add(breathing_session)
                print(f"   ✅ Created breathing session: {pattern_data['pattern_name']} ({pattern_data['duration_minutes']}min)")
            
            # Create emotional records
            print("\n😊 Creating emotional records...")
            emotional_data = [
                {
                    "emotion": "anxious",
                    "intensity": 7,
                    "triggers": ["work_deadline", "presentation"],
                    "notes": "Big presentation tomorrow. Feeling nervous but trying breathing exercises.",
                    "days_ago": 1,
                    "tags": ["work_stress", "presentation_anxiety", "breathing_helped"]
                },
                {
                    "emotion": "calm",
                    "intensity": 8,
                    "triggers": ["meditation", "breathing_exercise"],
                    "notes": "Morning meditation and breathing session helped set a peaceful tone for the day.",
                    "days_ago": 1,
                    "tags": ["morning_routine", "meditation", "peaceful"]
                },
                {
                    "emotion": "frustrated",
                    "intensity": 6,
                    "triggers": ["traffic", "running_late"],
                    "notes": "Stuck in traffic for 45 minutes. Late for appointment. Need better planning.",
                    "days_ago": 2,
                    "tags": ["traffic_stress", "time_management", "planning_needed"]
                },
                {
                    "emotion": "happy",
                    "intensity": 9,
                    "triggers": ["accomplishment", "praise"],
                    "notes": "Presentation went really well! Boss praised my preparation and delivery.",
                    "days_ago": 0,
                    "tags": ["success", "accomplishment", "work_achievement", "confidence_boost"]
                },
                {
                    "emotion": "tired",
                    "intensity": 8,
                    "triggers": ["poor_sleep", "caffeine_crash"],
                    "notes": "Didn't sleep well last night. Coffee isn't helping anymore.",
                    "days_ago": 3,
                    "tags": ["sleep_issues", "fatigue", "caffeine_dependence"]
                },
                {
                    "emotion": "grateful",
                    "intensity": 7,
                    "triggers": ["family_time", "support"],
                    "notes": "Family dinner was wonderful. Feeling thankful for their support during stressful time.",
                    "days_ago": 3,
                    "tags": ["family_support", "gratitude", "social_connection"]
                },
                {
                    "emotion": "overwhelmed",
                    "intensity": 8,
                    "triggers": ["multiple_deadlines", "meetings"],
                    "notes": "Three projects due this week plus back-to-back meetings. Need better time management.",
                    "days_ago": 5,
                    "tags": ["work_overload", "time_pressure", "multiple_tasks"]
                },
                {
                    "emotion": "peaceful",
                    "intensity": 9,
                    "triggers": ["nature_walk", "fresh_air"],
                    "notes": "Long walk in the park. Fresh air and nature sounds were exactly what I needed.",
                    "days_ago": 6,
                    "tags": ["nature_therapy", "outdoor_activity", "stress_relief"]
                }
            ]
            
            for emotion_data in emotional_data:
                record_time = datetime.now() - timedelta(days=emotion_data["days_ago"], hours=emotion_data.get("hours_offset", 0))
                emotional_record = EmotionalRecordModel(
                    user_id=test_user.id,
                    emotion=emotion_data["emotion"],
                    intensity=emotion_data["intensity"],
                    triggers=emotion_data["triggers"],
                    notes=emotion_data["notes"],
                    context_data={
                        "location": "home" if emotion_data["days_ago"] > 2 else "office",
                        "weather": "sunny" if emotion_data["days_ago"] % 2 == 0 else "cloudy",
                        "energy_level": emotion_data["intensity"]
                    },
                    tags=emotion_data["tags"],
                    tag_confidence=0.85,
                    processed_for_tags=True,
                    recorded_at=record_time
                )
                session.add(emotional_record)
                print(f"   ✅ Created emotional record: {emotion_data['emotion']} (intensity: {emotion_data['intensity']})")
            
            # Create user profile
            print("\n👤 Creating user profile...")
            user_profile = UserProfileModel(
                user_id=test_user.id,
                frequent_tags={
                    "stress_relief": 15,
                    "work_stress": 12,
                    "breathing_exercises": 10,
                    "anxiety_relief": 8,
                    "mindfulness": 7,
                    "focus": 6,
                    "accomplishment": 5
                },
                tag_categories={
                    "emotional": ["anxiety_relief", "stress_relief", "accomplishment", "gratitude"],
                    "behavioral": ["breathing_exercises", "meditation", "nature_therapy"],
                    "contextual": ["work_stress", "family_support", "morning_routine"],
                    "environmental": ["traffic_stress", "outdoor_activity"]
                },
                tag_trends={
                    "weekly_patterns": {
                        "monday": ["work_stress", "preparation"],
                        "tuesday": ["focus", "productivity"],
                        "wednesday": ["midweek_slump"],
                        "friday": ["accomplishment", "relief"],
                        "weekend": ["family_time", "relaxation"]
                    },
                    "emotional_progression": {
                        "stress_management": "improving",
                        "anxiety_levels": "decreasing",
                        "overall_wellbeing": "stable_positive"
                    }
                },
                personality_insights={
                    "stress_triggers": ["work_deadlines", "time_pressure", "public_speaking"],
                    "coping_mechanisms": ["breathing_exercises", "nature_walks", "family_support"],
                    "improvement_areas": ["time_management", "sleep_hygiene", "work_boundaries"],
                    "strengths": ["resilience", "self_awareness", "proactive_wellness"]
                },
                behavioral_patterns={
                    "breathing_session_preferences": {
                        "preferred_duration": "10-15 minutes",
                        "preferred_time": "morning and evening",
                        "most_effective_pattern": "4-7-8 breathing"
                    },
                    "emotional_cycles": {
                        "stress_peaks": "monday_wednesday",
                        "recovery_periods": "weekend",
                        "most_vulnerable_time": "afternoon_slump"
                    }
                },
                preferences={
                    "agent_interaction_style": "supportive and encouraging",
                    "reminder_frequency": "daily",
                    "preferred_techniques": ["breathing", "mindfulness", "gratitude"],
                    "privacy_level": "moderate"
                },
                total_interactions=23,
                unique_tags_count=18,
                last_tag_analysis=datetime.now() - timedelta(hours=6)
            )
            session.add(user_profile)
            print(f"   ✅ Created user profile with {user_profile.unique_tags_count} unique tags")
            
            # Create tag semantic data
            print("\n🏷️  Creating tag semantic relationships...")
            tag_semantics = [
                {
                    "tag": "stress_relief",
                    "category": "emotional",
                    "similar_tags": {
                        "anxiety_relief": 0.9,
                        "relaxation": 0.8,
                        "calm": 0.7,
                        "peaceful": 0.6
                    },
                    "synonyms": ["stress_reduction", "tension_relief", "relaxation"],
                    "related_concepts": ["mindfulness", "breathing", "meditation", "self_care"]
                },
                {
                    "tag": "work_stress",
                    "category": "contextual",
                    "similar_tags": {
                        "work_pressure": 0.9,
                        "deadline_stress": 0.8,
                        "professional_anxiety": 0.7
                    },
                    "synonyms": ["job_stress", "workplace_pressure", "professional_stress"],
                    "related_concepts": ["time_management", "work_life_balance", "productivity"]
                },
                {
                    "tag": "breathing_exercises",
                    "category": "behavioral",
                    "similar_tags": {
                        "meditation": 0.8,
                        "mindfulness": 0.7,
                        "relaxation_technique": 0.9
                    },
                    "synonyms": ["breath_work", "respiratory_exercises", "breathing_practice"],
                    "related_concepts": ["stress_management", "anxiety_reduction", "focus_improvement"]
                }
            ]
            
            for tag_data in tag_semantics:
                tag_semantic = TagSemanticModel(
                    tag=tag_data["tag"],
                    category=tag_data["category"],
                    similar_tags=tag_data["similar_tags"],
                    synonyms=tag_data["synonyms"],
                    related_concepts=tag_data["related_concepts"],
                    usage_count=15,
                    unique_users=1
                )
                session.add(tag_semantic)
                print(f"   ✅ Created semantic data for tag: {tag_data['tag']}")
            
            # Commit all changes
            await session.commit()
            print("\n🎉 Test data creation completed successfully!")
            
            # Print summary
            print("\n📊 Test Data Summary:")
            print(f"   👤 User: {test_user.email}")
            print(f"   🫁 Breathing Sessions: {len(breathing_patterns)}")
            print(f"   😊 Emotional Records: {len(emotional_data)}")
            print(f"   👤 User Profile: Complete with insights and patterns")
            print(f"   🏷️  Tag Semantics: {len(tag_semantics)} semantic relationships")
            print(f"\n🔑 Test Login Credentials:")
            print(f"   📧 Email: test@emotionai.com")
            print(f"   🔒 Password: testpass123")
        
        await db.close()
        
    except Exception as e:
        print(f"\n❌ Error creating test data: {e}")
        print(f"   Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    asyncio.run(create_test_data())