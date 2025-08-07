from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "EmotionAI API"
    debug: bool = False
    version: str = "1.0.0"
    
    # Database
    database_url: str = "postgresql://user:password@localhost/emotionai"
    database_echo: bool = False
    
    # Redis (for caching and sessions)
    redis_url: str = "redis://localhost:6379"
    
    # Vector Database
    vector_db_type: str = "chromadb"  # chromadb or qdrant
    chromadb_path: str = "./data/chromadb"
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    default_llm_model: str = "gpt-4o"
    max_tokens: int = 500
    temperature: float = 0.7
    
    # Authentication
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Agent Configuration
    max_memory_items: int = 100
    memory_cleanup_interval: int = 3600  # seconds
    agent_timeout: int = 30  # seconds
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour in seconds
    
    # AWS Configuration (for DynamoDB if needed)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

# Ensure required directories exist
os.makedirs(os.path.dirname(settings.chromadb_path), exist_ok=True) 