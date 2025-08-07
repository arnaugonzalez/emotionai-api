from fastapi import FastAPI
import logging
from contextlib import asynccontextmanager

from .database import engine
from . import models
from .routers import auth, emotional_records, breathing_sessions, breathing_patterns, custom_emotions, ai_conversation_memories, daily_token_usage
from .config import settings

# Import agent system
from core.llm_factory import LLMFactory
from services.agent_manager import AgentManager
from api.agents import router as agents_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global variables for dependency injection
llm_factory = None
agent_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global llm_factory, agent_manager
    
    # Startup
    logger.info("Starting EmotionAI API...")
    
    # Create database tables
    models.Base.metadata.create_all(bind=engine)
    
    # Initialize LLM factory and agent manager
    llm_factory = LLMFactory()
    agent_manager = AgentManager(llm_factory)
    
    logger.info("EmotionAI API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down EmotionAI API...")
    if agent_manager:
        await agent_manager.shutdown()
    logger.info("EmotionAI API shutdown complete")

app = FastAPI(
    title="EmotionAI API",
    description="AI-powered mental health and wellness API with personalized agents",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(emotional_records.router, prefix="/emotional_records", tags=["emotional_records"])
app.include_router(breathing_sessions.router, prefix="/breathing_sessions", tags=["breathing_sessions"])
app.include_router(breathing_patterns.router, prefix="/breathing_patterns", tags=["breathing_patterns"])
app.include_router(custom_emotions.router, prefix="/custom_emotions", tags=["custom_emotions"])
app.include_router(ai_conversation_memories.router, prefix="/ai_conversation_memories", tags=["ai_conversation_memories"])
app.include_router(daily_token_usage.router, prefix="/daily_token_usage", tags=["daily_token_usage"])

# Include agent router
app.include_router(agents_router, tags=["agents"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to the EmotionAI API",
        "version": "1.0.0",
        "description": "AI-powered mental health and wellness API",
        "endpoints": {
            "auth": "/auth",
            "agents": "/agents",
            "emotional_records": "/emotional_records",
            "breathing_sessions": "/breathing_sessions",
            "breathing_patterns": "/breathing_patterns",
            "custom_emotions": "/custom_emotions",
            "ai_conversations": "/ai_conversation_memories",
            "token_usage": "/daily_token_usage",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_manager_active": agent_manager is not None,
        "llm_factory_active": llm_factory is not None
    }