#!/usr/bin/env python3
"""
Integration Test Script for EmotionAI API

This script tests the key components of the merged agent system
to ensure the migration was successful.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_import_components():
    """Test that all major components can be imported"""
    print("🔍 Testing component imports...")
    
    try:
        # Test agent imports
        from agents.base_agent import BasePersonalizedAgent
        from agents.therapy_agent import TherapyAgent
        from agents.wellness_agent import WellnessAgent
        print("  ✅ Agent classes imported successfully")
        
        # Test core components
        from core.llm_factory import LLMFactory
        from services.agent_manager import AgentManager
        print("  ✅ Core components imported successfully")
        
        # Test API components
        from api.agents import router
        print("  ✅ API components imported successfully")
        
        # Test models and schemas
        from app.models import User, EmotionalRecord, BreathingSession
        from app.schemas import ChatResponse, AgentStatus
        from models.responses import AgentResponse, ChatMessage
        print("  ✅ Models and schemas imported successfully")
        
        # Test configuration
        from app.config import settings
        print("  ✅ Configuration imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

async def test_llm_factory():
    """Test LLM Factory functionality"""
    print("\n🏭 Testing LLM Factory...")
    
    try:
        from core.llm_factory import LLMFactory
        
        factory = LLMFactory()
        print("  ✅ LLM Factory created successfully")
        
        # Test available providers
        providers = factory.get_available_providers()
        print(f"  📋 Available providers: {providers}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ LLM Factory error: {e}")
        return False

async def test_agent_creation():
    """Test agent creation (without LLM calls)"""
    print("\n🤖 Testing agent creation...")
    
    try:
        from agents.therapy_agent import TherapyAgent
        from agents.wellness_agent import WellnessAgent
        from unittest.mock import Mock
        
        # Mock LLM for testing
        mock_llm = Mock()
        
        # Test TherapyAgent
        therapy_agent = TherapyAgent(
            user_id=1,
            llm=mock_llm,
            personality="empathetic_supportive"
        )
        print("  ✅ TherapyAgent created successfully")
        
        # Test WellnessAgent
        wellness_agent = WellnessAgent(
            user_id=1,
            llm=mock_llm,
            personality="mindful_contemplative"
        )
        print("  ✅ WellnessAgent created successfully")
        
        # Test system prompts
        therapy_prompt = therapy_agent.get_system_prompt()
        wellness_prompt = wellness_agent.get_system_prompt()
        
        print(f"  📝 TherapyAgent prompt length: {len(therapy_prompt)} chars")
        print(f"  📝 WellnessAgent prompt length: {len(wellness_prompt)} chars")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Agent creation error: {e}")
        return False

async def test_database_models():
    """Test database model definitions"""
    print("\n🗄️ Testing database models...")
    
    try:
        from app.models import User, EmotionalRecord, BreathingSession
        
        # Test User model fields
        user_fields = [attr for attr in dir(User) if not attr.startswith('_')]
        required_user_fields = ['agent_personality', 'profile_data', 'agent_preferences']
        
        for field in required_user_fields:
            if field in user_fields:
                print(f"  ✅ User.{field} field exists")
            else:
                print(f"  ❌ User.{field} field missing")
                return False
        
        # Test EmotionalRecord model fields
        emotion_fields = [attr for attr in dir(EmotionalRecord) if not attr.startswith('_')]
        required_emotion_fields = ['emotion_type', 'intensity', 'context']
        
        for field in required_emotion_fields:
            if field in emotion_fields:
                print(f"  ✅ EmotionalRecord.{field} field exists")
            else:
                print(f"  ❌ EmotionalRecord.{field} field missing")
                return False
        
        # Test BreathingSession model fields
        breathing_fields = [attr for attr in dir(BreathingSession) if not attr.startswith('_')]
        required_breathing_fields = ['pattern_name', 'duration_seconds', 'session_data']
        
        for field in required_breathing_fields:
            if field in breathing_fields:
                print(f"  ✅ BreathingSession.{field} field exists")
            else:
                print(f"  ❌ BreathingSession.{field} field missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Database model error: {e}")
        return False

async def test_api_schemas():
    """Test API schema definitions"""
    print("\n📋 Testing API schemas...")
    
    try:
        from models.responses import ChatResponse, AgentResponse, ChatMessage
        from app.schemas import User, EmotionalRecord, BreathingSessionData
        
        # Test response models
        print("  ✅ ChatResponse schema available")
        print("  ✅ AgentResponse schema available") 
        print("  ✅ ChatMessage schema available")
        print("  ✅ User schema available")
        print("  ✅ EmotionalRecord schema available")
        print("  ✅ BreathingSessionData schema available")
        
        return True
        
    except Exception as e:
        print(f"  ❌ API schema error: {e}")
        return False

async def test_configuration():
    """Test configuration loading"""
    print("\n⚙️ Testing configuration...")
    
    try:
        from app.config import settings
        
        # Test required settings
        config_checks = {
            'app_name': settings.app_name,
            'database_url': settings.database_url,
            'secret_key': settings.secret_key,
            'max_memory_items': settings.max_memory_items,
            'agent_timeout': settings.agent_timeout,
        }
        
        for setting, value in config_checks.items():
            if value is not None:
                print(f"  ✅ {setting}: {value}")
            else:
                print(f"  ⚠️ {setting}: Not set")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Configuration error: {e}")
        return False

async def main():
    """Run all integration tests"""
    print("🚀 EmotionAI API Integration Test Suite")
    print("=" * 50)
    
    tests = [
        test_import_components,
        test_llm_factory,
        test_agent_creation,
        test_database_models,
        test_api_schemas,
        test_configuration,
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The migration was successful.")
        return 0
    else:
        print("⚠️ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main()) 