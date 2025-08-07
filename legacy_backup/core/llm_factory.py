from typing import Optional, Dict, Any
from langchain.chat_models import ChatOpenAI, ChatAnthropic
from langchain.chat_models.base import BaseChatModel
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class LLMFactory:
    """Factory for creating and managing LLM instances"""
    
    def __init__(self):
        self._llm_cache: Dict[str, BaseChatModel] = {}
        self.default_provider = "openai"
        
    async def get_llm(
        self, 
        provider: str = None,
        model: str = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> BaseChatModel:
        """Get an LLM instance with caching"""
        
        # Use defaults if not specified
        provider = provider or self.default_provider
        model = model or settings.default_llm_model
        temperature = temperature or settings.temperature
        max_tokens = max_tokens or settings.max_tokens
        
        # Create cache key
        cache_key = f"{provider}_{model}_{temperature}_{max_tokens}"
        
        # Return cached instance if available
        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]
        
        # Create new instance
        llm = self._create_llm(provider, model, temperature, max_tokens)
        
        # Cache the instance
        self._llm_cache[cache_key] = llm
        
        logger.info(f"Created LLM instance: {provider}/{model}")
        return llm
    
    def _create_llm(
        self, 
        provider: str, 
        model: str, 
        temperature: float, 
        max_tokens: int
    ) -> BaseChatModel:
        """Create a new LLM instance"""
        
        if provider == "openai":
            return ChatOpenAI(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                openai_api_key=settings.openai_api_key,
                request_timeout=30
            )
        
        elif provider == "anthropic":
            if not settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            
            return ChatAnthropic(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                anthropic_api_key=settings.anthropic_api_key
            )
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def clear_cache(self):
        """Clear the LLM cache"""
        self._llm_cache.clear()
        logger.info("LLM cache cleared")
    
    def get_available_providers(self) -> Dict[str, bool]:
        """Get available LLM providers and their status"""
        return {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key)
        } 