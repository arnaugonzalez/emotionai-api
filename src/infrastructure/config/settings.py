"""
Application Settings

Centralized configuration management for the clean architecture.
Settings are loaded from environment variables and configuration files.
"""

from pydantic_settings import BaseSettings
from typing import Optional, Dict, Any, List
import os
from pydantic import Field, field_validator
from src import __version__ as app_version

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "EmotionAI FastAPI"
    debug: bool = False
    version: str = app_version
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    class Config:
        env_file = "/etc/emotionai-api.env"
        case_sensitive = False
        env_prefix = ""
        extra = "ignore"  # Ignore extra fields instead of raising errors
    
    # Database
    database_url: str = Field(None, env="DATABASE_URL")
    async_database_url: str = Field(None, env="ASYNC_DATABASE_URL")
    db_ssl_root_cert = "/etc/ssl/certs/aws-rds.pem"
    database_echo: bool = False
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis (for caching and event bus)
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # LLM Configuration
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_max_tokens: int = Field(default=500, env="OPENAI_MAX_TOKENS")
    openai_temperature: float = Field(default=0.7, env="OPENAI_TEMPERATURE")
    llm_timeout: int = 30

    # Anthropic Claude (optional)
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-5-sonnet-latest", env="ANTHROPIC_MODEL")
    
    # Authentication
    secret_key: str = Field(default="your-secret-key-here-change-in-production", env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Agent Configuration
    max_memory_items: int = 100
    memory_cleanup_interval: int = 3600  # seconds
    agent_timeout: int = 30  # seconds
    max_active_agents: int = 1000
    
    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour in seconds
    
    # AWS Configuration (if using DynamoDB or S3)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = Field(default="us-west-1", env="AWS_REGION")
    
    # Monitoring & Observability
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    enable_metrics: bool = True
    metrics_port: int = 8080
    health_check_interval: int = 60
    
    # Security
    cors_origins: List[str] = ["*"]
    trusted_hosts: List[str] = Field(default_factory=lambda: ["*"], env="TRUSTED_HOSTS")
    enable_https_redirect: bool = False

    # EC2
    ec2_public_ip: Optional[str] = Field(default=None, env="EC2_PUBLIC_IP")

    
    # Normalize TRUSTED_HOSTS from comma-separated string, if provided
    @field_validator("trusted_hosts", mode="before")
    @classmethod
    def _parse_trusted_hosts(cls, v):
        if isinstance(v, str):
            items = [s.strip() for s in v.split(",") if s.strip()]
            return items or ["*"]
        return v
    
    # Feature Flags
    enable_event_bus: bool = True
    enable_analytics: bool = True
    
    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """Initialize settings with optional overrides"""
        super().__init__()
        
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(self, key):
                    setattr(self, key, value)
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment.lower() == "testing"
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration dictionary"""
        return {
            "url": self.database_url,
            "echo": self.database_echo,
            "pool_size": self.database_pool_size,
            "max_overflow": self.database_max_overflow
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration dictionary"""
        return {
            "url": self.redis_url,
            "db": self.redis_db,
            "password": self.redis_password
        }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration dictionary"""
        return {
            "provider": "anthropic" if self.anthropic_api_key else "openai",
            "timeout": self.llm_timeout,
            "openai": {
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "max_tokens": self.openai_max_tokens,
                "temperature": self.openai_temperature,
            },
            "anthropic": {
                "api_key": self.anthropic_api_key,
                "model": self.anthropic_model,
            },
        }
    
    def validate_required_settings(self) -> None:
        """Validate that required settings are present"""
        required_settings = []

        if not self.secret_key or self.secret_key == "your-secret-key-here-change-in-production":
            required_settings.append("SECRET_KEY")

        # Require at least one LLM provider key
        if not (self.openai_api_key or self.anthropic_api_key):
            required_settings.append("OPENAI_API_KEY or ANTHROPIC_API_KEY")

        if self.is_production and self.debug:
            required_settings.append("DEBUG should be False in production")

        if required_settings:
            raise ValueError(f"Missing required settings: {', '.join(required_settings)}")


def create_settings(config_overrides: Optional[Dict[str, Any]] = None) -> Settings:
    """Create and validate settings instance"""
    settings = Settings(config_overrides)
    
    # Validate settings only in production
    if settings.is_production:
        settings.validate_required_settings()
    
    return settings


# Global settings instance (can be overridden for testing)
settings = create_settings() 