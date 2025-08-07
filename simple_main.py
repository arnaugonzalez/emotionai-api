"""
Simple EmotionAI API for Phone Testing
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="EmotionAI API - Simple",
    description="Simplified version for phone testing",
    version="2.0.0"
)

# CORS for phone connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ChatRequest(BaseModel):
    agent_type: str = "therapy"
    message: str
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    message: str
    agent_type: str
    conversation_id: str
    # Removed crisis_detected - replaced by intelligent tagging
    suggestions: list = []
    timestamp: str

class UserRegister(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
    user: Dict[str, Any]

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "EmotionAI API - Clean Architecture (Simple)",
        "version": "2.0.0",
        "status": "running",
        "phone_url": "Use http://10.0.2.2:8000 from AVD or http://YOUR_IP:8000 from phone"
    }

# Health endpoints
@app.get("/health/")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "2.0.0",
        "environment": "development"
    }

@app.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "components": {
            "api": {"status": "healthy"},
            "database": {"status": "healthy"}, 
            "agents": {"status": "healthy"}
        },
        "response_time_ms": 50
    }

# Auth endpoints
@app.post("/auth/register", response_model=TokenResponse)
async def register(user: UserRegister):
    logger.info(f"User registration: {user.email}")
    return TokenResponse(
        access_token="test_token_123",
        user={
            "id": "user_123",
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_verified": True
        }
    )

@app.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    logger.info(f"User login: {credentials.email}")
    return TokenResponse(
        access_token="test_token_123",
        user={
            "id": "user_123",
            "email": credentials.email,
            "first_name": "Test",
            "last_name": "User",
            "is_verified": True
        }
    )

# Chat endpoints
@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    logger.info(f"Chat request: {request.agent_type} - {request.message}")
    
    # Simple agent responses
    responses = {
        "therapy": f"I understand you're saying '{request.message}'. How does that make you feel? As your therapy agent, I'm here to support you.",
        "wellness": f"Thank you for sharing '{request.message}'. Let's focus on your wellbeing. Have you tried any breathing exercises today?"
    }
    
    response_text = responses.get(request.agent_type, f"Hello! I'm here to help with your {request.agent_type} needs. You said: {request.message}")
    
    return ChatResponse(
        message=response_text,
        agent_type=request.agent_type,
        conversation_id="conv_123",
        suggestions=["Tell me more", "How can I help?", "Let's explore this further"],
        timestamp="2024-01-01T00:00:00Z"
    )

@app.get("/api/v1/agents")
async def list_agents():
    return {
        "agents": [
            {
                "type": "therapy",
                "name": "Therapy Agent",
                "description": "Provides therapeutic conversations and emotional support",
                "capabilities": ["emotional_support", "coping_strategies", "intelligent_tagging"]
            },
            {
                "type": "wellness",
                "name": "Wellness Agent", 
                "description": "Focuses on mindfulness, breathing exercises, and general wellness",
                "capabilities": ["mindfulness", "breathing_exercises", "wellness_tips"]
            }
        ]
    }

@app.get("/api/v1/agents/{agent_type}/status")
async def get_agent_status(agent_type: str):
    return {
        "agent_type": agent_type,
        "status": "active",
        "last_interaction": "2024-01-01T00:00:00Z",
        "memory_items": 5,
        "response_time_ms": 150
    }

# Data Management Endpoints (Mock implementations)
@app.get("/emotional_records/")
async def get_emotional_records():
    return [
        {
            "id": "1",  # String ID for Flutter compatibility
            "source": "manual",  # Required by Flutter model
            "emotion": "happy",
            "intensity": 8,
            "description": "Feeling great today",
            "created_at": "2024-01-01T12:00:00Z",
            "color": 16766720,  # #FFD700 as int for Flutter
            "custom_emotion_name": None,
            "custom_emotion_color": None
        },
        {
            "id": "2",  # String ID for Flutter compatibility
            "source": "manual",  # Required by Flutter model
            "emotion": "calm",
            "intensity": 6,
            "description": "Peaceful moment",
            "created_at": "2024-01-01T14:00:00Z",
            "color": 8900331,  # #87CEEB as int for Flutter
            "custom_emotion_name": None,
            "custom_emotion_color": None
        }
    ]

@app.post("/emotional_records/")
async def create_emotional_record(record: dict):
    record["id"] = "100"  # String ID for Flutter compatibility
    record["created_at"] = "2024-01-01T12:00:00Z"
    return record

@app.get("/breathing_sessions/")
async def get_breathing_sessions():
    return [
        {
            "id": "1",  # String ID for Flutter compatibility
            "pattern": "4-7-8 Breathing",  # Pattern name, not ID for Flutter
            "rating": 4.0,  # Double for Flutter compatibility
            "comment": "Good session",  # Flutter uses 'comment' not 'notes'
            "created_at": "2024-01-01T12:00:00Z"
        },
        {
            "id": "2",  # String ID for Flutter compatibility
            "pattern": "Box Breathing",  # Pattern name, not ID for Flutter
            "rating": 5.0,  # Double for Flutter compatibility
            "comment": "Very relaxing",  # Flutter uses 'comment' not 'notes'
            "created_at": "2024-01-01T14:00:00Z"
        }
    ]

@app.post("/breathing_sessions/")
async def create_breathing_session(session: dict):
    session["id"] = "200"  # String ID for Flutter compatibility
    session["created_at"] = "2024-01-01T12:00:00Z"
    return session

@app.get("/breathing_patterns/")
async def get_breathing_patterns():
    return [
        {
            "id": "1",  # String ID for Flutter compatibility
            "name": "4-7-8 Breathing",
            "inhale_seconds": 4,  # Flutter expects 'seconds' not 'duration'
            "hold_seconds": 7,
            "exhale_seconds": 8,
            "cycles": 4,
            "rest_seconds": 0  # Flutter requires rest_seconds field
        },
        {
            "id": "2",  # String ID for Flutter compatibility
            "name": "Box Breathing",
            "inhale_seconds": 4,  # Flutter expects 'seconds' not 'duration'
            "hold_seconds": 4,
            "exhale_seconds": 4,
            "cycles": 6,
            "rest_seconds": 0  # Flutter requires rest_seconds field
        }
    ]

@app.post("/breathing_patterns/")
async def create_breathing_pattern(pattern: dict):
    pattern["id"] = "300"  # String ID for Flutter compatibility
    return pattern

@app.get("/custom_emotions/")
async def get_custom_emotions():
    return [
        {
            "id": "1",  # String ID for Flutter compatibility
            "name": "Excited",
            "color": 16737355,  # #FF6B6B as int for Flutter
            "created_at": "2024-01-01T12:00:00Z"
        },
        {
            "id": "2",  # String ID for Flutter compatibility
            "name": "Contemplative",
            "color": 5164100,  # #4ECDC4 as int for Flutter
            "created_at": "2024-01-01T12:00:00Z"
        }
    ]

@app.post("/custom_emotions/")
async def create_custom_emotion(emotion: dict):
    emotion["id"] = "400"  # String ID for Flutter compatibility
    emotion["created_at"] = "2024-01-01T12:00:00Z"
    return emotion

# User limitations endpoint
@app.get("/user/limitations")
async def get_user_limitations():
    return {
        "daily_records_limit": 50,
        "monthly_records_limit": 1000,
        "current_daily_records": 5,
        "current_monthly_records": 45,
        "premium": False,
        "can_add_records": True,
        "can_add_sessions": True,
        "can_add_custom_emotions": True,
        "reset_date": "2024-01-02T00:00:00Z"
    }

# Test endpoint for phone connectivity
@app.get("/test/phone")
async def test_phone_connection():
    return {
        "message": "✅ Phone connection successful!",
        "your_ip": "Connected successfully",
        "instructions": [
            "✅ Backend is running",
            "✅ CORS is enabled", 
            "✅ All endpoints working",
            "✅ Data endpoints added",
            "✅ User limitations added",
            "🚀 Your Flutter app can now connect!"
        ]
    }

if __name__ == "__main__":
    print("🚀 Starting EmotionAI API for phone testing...")
    print("📱 Phone/AVD URL: http://10.0.2.2:8000")
    print("💻 Local URL: http://localhost:8000")
    print("🌐 Network URL: http://192.168.1.180:8000")  # Your IP from ipconfig
    print("🔗 Test connection: http://localhost:8000/test/phone")
    
    uvicorn.run(
        "simple_main:app",
        host="0.0.0.0",  # Important: Bind to all interfaces for network access
        port=8000,
        log_level="info",
        reload=True
    ) 