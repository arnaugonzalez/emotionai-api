"""LLM Provider Factory"""

from typing import Dict, Any

class LLMProviderFactory:
    def __init__(self, settings):
        self.settings = settings
    
    def get_provider(self, provider_type: str = "openai"):
        return MockLLMProvider()
    
    async def health_check(self) -> Dict[str, Any]:
        return {"status": "healthy", "providers": ["openai", "anthropic"]}

class MockLLMProvider:
    def __init__(self):
        pass
    
    async def generate(self, prompt: str) -> str:
        return f"Mock response to: {prompt}"
    
    async def health_check(self) -> bool:
        return True 