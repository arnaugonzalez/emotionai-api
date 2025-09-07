"""
Dependency Injection Container

Centralized configuration and wiring of all application dependencies.
Implements the Composition Root pattern for clean dependency management.
"""

from dataclasses import dataclass
from typing import Dict, Any, Protocol
import asyncio
import logging

# Domain interfaces
from ..domain.users.interfaces import IUserRepository
from ..domain.events.interfaces import IEventRepository
from ..domain.records.interfaces import IEmotionalRecordRepository
from ..domain.breathing.interfaces import IBreathingSessionRepository
from ..domain.chat.interfaces import IAgentConversationRepository
from ..domain.analytics.interfaces import IAnalyticsRepository

# Application services
from ..application.chat.use_cases.agent_chat_use_case import AgentChatUseCase
from ..application.usage.use_cases.get_monthly_usage_use_case import GetMonthlyUsageUseCase
from ..application.services.agent_service import IAgentService
from ..application.services.event_bus import IEventBus
from ..application.services.tagging_service import ITaggingService
from ..application.services.user_knowledge_service import IUserKnowledgeService
from ..application.services.similarity_search_service import ISimilaritySearchService
from ..application.services.profile_service import IProfileService

# Infrastructure implementations
from .repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository
from .records.repositories.sqlalchemy_emotional_repository import SqlAlchemyEmotionalRepository
from .breathing.repositories.sqlalchemy_breathing_repository import SqlAlchemyBreathingRepository
from .conversations.repositories.sqlalchemy_conversation_repository import SqlAlchemyConversationRepository
from .events.repositories.sqlalchemy_event_repository import SqlAlchemyEventRepository
from .analytics.repositories.sqlalchemy_analytics_repository import SqlAlchemyAnalyticsRepository

from .services.langchain_agent_service import LangChainAgentService
from .services.openai_llm_service import OpenAILLMService
from .services.anthropic_llm_service import AnthropicLLMService
from .services.redis_event_bus import RedisEventBus
from .tagging.services.openai_tagging_service import OpenAITaggingService
from .usage.repositories.sqlalchemy_token_usage_repository import SqlAlchemyTokenUsageRepository
from .services.mock_user_knowledge_service import MockUserKnowledgeService
from .services.mock_similarity_search_service import MockSimilaritySearchService
from .services.profile_service import ProfileService

from .config.settings import Settings
from .database.connection import DatabaseConnection
from .external.llm_providers import LLMProviderFactory

logger = logging.getLogger(__name__)


@dataclass
class ApplicationContainer:
    """
    Dependency injection container that wires all application components.
    
    This implements the Composition Root pattern, centralizing all dependency
    configuration in one place for better maintainability and testability.
    """
    
    # Core infrastructure
    settings: Settings
    database: DatabaseConnection
    llm_factory: LLMProviderFactory
    
    # Repositories
    user_repository: IUserRepository
    emotional_repository: IEmotionalRecordRepository
    breathing_repository: IBreathingSessionRepository
    conversation_repository: IAgentConversationRepository
    event_repository: IEventRepository
    analytics_repository: IAnalyticsRepository
    token_usage_repository: Any
    
    # Services
    agent_service: IAgentService
    event_bus: IEventBus
    tagging_service: ITaggingService
    user_knowledge_service: IUserKnowledgeService
    similarity_search_service: ISimilaritySearchService
    profile_service: IProfileService
    
    # Use cases
    agent_chat_use_case: AgentChatUseCase
    get_monthly_usage_use_case: Any
    
    @classmethod
    async def create(cls, config_overrides: Dict[str, Any] = None) -> 'ApplicationContainer':
        """
        Factory method to create and configure the entire application.
        
        This method follows the dependency injection pattern, creating all
        dependencies in the correct order and wiring them together.
        """
        
        logger.info("Initializing application container...")
        
        # 1. Load settings
        settings = Settings(config_overrides or {})
        
        # 2. Initialize core infrastructure
        database = await DatabaseConnection.create(settings)
        llm_factory = LLMProviderFactory(settings)
        
        # 3. Initialize repositories (data layer)
        user_repository = SqlAlchemyUserRepository(database)
        emotional_repository = SqlAlchemyEmotionalRepository(database)
        breathing_repository = SqlAlchemyBreathingRepository(database)
        conversation_repository = SqlAlchemyConversationRepository(database)
        event_repository = SqlAlchemyEventRepository(database)
        analytics_repository = SqlAlchemyAnalyticsRepository(database)
        token_usage_repository = SqlAlchemyTokenUsageRepository(database)
        
        # 4. Initialize external services
        event_bus = RedisEventBus(settings.redis_url)
        
        # 5. Initialize application services
        # Initialize LLM service (prefer Anthropic if configured)
        if settings.anthropic_api_key:
            llm_service = AnthropicLLMService(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
            )
            logger.info("Using Anthropic Claude as the default LLM provider")
        else:
            llm_service = OpenAILLMService(
                api_key=settings.openai_api_key,
                model=settings.openai_model,
            )
            logger.info("Using OpenAI as the default LLM provider")
        
        # Initialize agent service with real LLM and conversation repository
        agent_service = LangChainAgentService(
            llm_service=llm_service,
            conversation_repository=conversation_repository,
            user_repository=user_repository,
            emotional_repository=emotional_repository,
            settings=settings
        )
        
        # Initialize intelligent tagging services
        tagging_service = OpenAITaggingService(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            token_usage_repo=token_usage_repository
        )
        
        # Initialize mock services (to be replaced with full implementations)
        user_knowledge_service = MockUserKnowledgeService()
        similarity_search_service = MockSimilaritySearchService()
        
        # Initialize profile service
        profile_service = ProfileService(database)
        
        # 6. Initialize use cases (business logic orchestration)
        agent_chat_use_case = AgentChatUseCase(
            user_repository=user_repository,
            emotional_repository=emotional_repository,
            breathing_repository=breathing_repository,
            conversation_repository=conversation_repository,
            event_repository=event_repository,
            agent_service=agent_service,
            tagging_service=tagging_service,
            user_knowledge_service=user_knowledge_service,
            similarity_search_service=similarity_search_service
        )
        get_monthly_usage_use_case = GetMonthlyUsageUseCase(token_usage_repository)
        
        # 7. Start background services
        await event_bus.start()
        
        container = cls(
            settings=settings,
            database=database,
            llm_factory=llm_factory,
            user_repository=user_repository,
            emotional_repository=emotional_repository,
            breathing_repository=breathing_repository,
            conversation_repository=conversation_repository,
            event_repository=event_repository,
            analytics_repository=analytics_repository,
            agent_service=agent_service,
            event_bus=event_bus,
            tagging_service=tagging_service,
            user_knowledge_service=user_knowledge_service,
            similarity_search_service=similarity_search_service,
            profile_service=profile_service,
            agent_chat_use_case=agent_chat_use_case,
            token_usage_repository=token_usage_repository,
            get_monthly_usage_use_case=get_monthly_usage_use_case
        )
        
        logger.info("Application container initialized successfully")
        return container
    
    async def shutdown(self) -> None:
        """Gracefully shutdown all services"""
        logger.info("Shutting down application container...")
        
        try:
            # Stop background services
            await self.event_bus.stop()
            
            # Close database connections
            await self.database.close()
            
            # Cleanup agent service
            await self.agent_service.cleanup()
            
            logger.info("Application container shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during container shutdown: {e}")
            raise
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check of all components"""
        health_status = {
            "status": "healthy",
            "components": {}
        }
        
        try:
            # Check database
            db_healthy = await self.database.health_check()
            db_details: Dict[str, Any] = {"status": "healthy" if db_healthy else "unhealthy"}
            if db_healthy:
                # Include entity counts for observability (non-fatal if fails)
                try:
                    db_details["entity_counts"] = await self.database.get_entity_counts()
                except Exception:
                    pass
            health_status["components"]["database"] = db_details
            
            # Check LLM providers
            llm_status = await self.llm_factory.health_check()
            health_status["components"]["llm_providers"] = llm_status
            
            # Check event bus
            event_bus_healthy = await self.event_bus.health_check()
            health_status["components"]["event_bus"] = {
                "status": "healthy" if event_bus_healthy else "unhealthy"
            }
            
            # Check agent service
            agent_service_healthy = await self.agent_service.health_check()
            health_status["components"]["agent_service"] = {
                "status": "healthy" if agent_service_healthy else "unhealthy",
                "active_agents": await self.agent_service.get_active_agent_count()
            }
            
            # Overall status
            all_healthy = all(
                comp["status"] == "healthy" 
                for comp in health_status["components"].values()
                if isinstance(comp, dict) and "status" in comp
            )
            
            if not all_healthy:
                health_status["status"] = "degraded"
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get application metrics"""
        return {
            "active_agents": self.agent_service.get_active_agent_count(),
            "database_pool_size": self.database.get_pool_size(),
            "memory_usage": self._get_memory_usage(),
            "uptime": self._get_uptime()
        }
    
    def _get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }
    
    def _get_uptime(self) -> float:
        """Get application uptime in seconds"""
        if not hasattr(self, '_start_time'):
            import time
            self._start_time = time.time()
        
        import time
        return time.time() - self._start_time


# Global container instance (initialized at startup)
_container: ApplicationContainer = None


async def get_container() -> ApplicationContainer:
    """Get the global application container"""
    global _container
    if _container is None:
        _container = await ApplicationContainer.create()
    return _container


async def initialize_container(config_overrides: Dict[str, Any] = None) -> ApplicationContainer:
    """Initialize the global application container"""
    global _container
    if _container is not None:
        await _container.shutdown()
    
    _container = await ApplicationContainer.create(config_overrides)
    return _container


async def shutdown_container() -> None:
    """Shutdown the global application container"""
    global _container
    if _container is not None:
        await _container.shutdown()
        _container = None 