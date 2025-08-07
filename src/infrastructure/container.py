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
from ..domain.repositories.interfaces import (
    IUserRepository,
    IEmotionalRecordRepository, 
    IBreathingSessionRepository,
    IAgentConversationRepository,
    IEventRepository,
    IAnalyticsRepository
)

# Application services
from ..application.use_cases.agent_chat_use_case import AgentChatUseCase
from ..application.services.agent_service import IAgentService
from ..application.services.event_bus import IEventBus
from ..application.services.tagging_service import ITaggingService
from ..application.services.user_knowledge_service import IUserKnowledgeService
from ..application.services.similarity_search_service import ISimilaritySearchService

# Infrastructure implementations
from .repositories.sqlalchemy_user_repository import SqlAlchemyUserRepository
from .repositories.sqlalchemy_emotional_repository import SqlAlchemyEmotionalRepository
from .repositories.sqlalchemy_breathing_repository import SqlAlchemyBreathingRepository
from .repositories.sqlalchemy_conversation_repository import SqlAlchemyConversationRepository
from .repositories.sqlalchemy_event_repository import SqlAlchemyEventRepository
from .repositories.sqlalchemy_analytics_repository import SqlAlchemyAnalyticsRepository

from .services.langchain_agent_service import LangChainAgentService
from .services.redis_event_bus import RedisEventBus
from .services.openai_tagging_service import OpenAITaggingService
from .services.mock_user_knowledge_service import MockUserKnowledgeService
from .services.mock_similarity_search_service import MockSimilaritySearchService

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
    
    # Services
    agent_service: IAgentService
    event_bus: IEventBus
    tagging_service: ITaggingService
    user_knowledge_service: IUserKnowledgeService
    similarity_search_service: ISimilaritySearchService
    
    # Use cases
    agent_chat_use_case: AgentChatUseCase
    
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
        
        # 4. Initialize external services
        event_bus = RedisEventBus(settings.redis_url)
        
        # 5. Initialize application services
        agent_service = LangChainAgentService(
            llm_factory=llm_factory,
            settings=settings
        )
        
        # Initialize intelligent tagging services
        tagging_service = OpenAITaggingService(
            api_key=settings.openai_api_key,
            model=settings.default_llm_model
        )
        
        # Initialize mock services (to be replaced with full implementations)
        user_knowledge_service = MockUserKnowledgeService()
        similarity_search_service = MockSimilaritySearchService()
        
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
            agent_chat_use_case=agent_chat_use_case
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
            health_status["components"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy"
            }
            
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