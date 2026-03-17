"""LLM Provider Factory

Delegates to the real LLM service registered at startup rather than
returning a hardcoded mock.
"""

import logging
from typing import Any, Dict, Optional

from ..services.openai_llm_service import OpenAILLMService

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Thin wrapper that holds a reference to the active LLM service."""

    def __init__(self, settings: Any):
        self.settings = settings
        self._llm_service: Optional[Any] = None

    def register_service(self, service: Any) -> None:
        """Called by the container after creating the real LLM service."""
        self._llm_service = service

    def get_provider(self, provider_type: str = "openai") -> Any:
        if self._llm_service is not None:
            return self._llm_service
        raise RuntimeError(
            "No LLM service registered. Call register_service() first."
        )

    async def health_check(self) -> Dict[str, Any]:
        if self._llm_service is not None:
            try:
                healthy = await self._llm_service.health_check()
                return {"status": "healthy" if healthy else "unhealthy"}
            except Exception as exc:
                logger.error(f"LLM health check failed: {exc}")
                return {"status": "unhealthy", "error": str(exc)}
        return {"status": "unhealthy", "error": "no LLM service registered"}
