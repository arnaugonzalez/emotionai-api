"""
OpenAI LLM Service Implementation

Provides real AI-powered therapeutic responses using OpenAI's GPT models.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
import openai
from openai import AsyncOpenAI

from ...domain.chat.entities import AgentContext, TherapyResponse, Message
from ...application.services.llm_service import ILLMService

logger = logging.getLogger(__name__)


class OpenAILLMService(ILLMService):
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        logger.info(f"OpenAI LLM Service initialized with model: {model}")

    async def generate_therapy_response(
        self, 
        context: AgentContext, 
        user_message: str
    ) -> TherapyResponse:
        """Generate a therapeutic response using OpenAI"""
        try:
            # Build the conversation context
            conversation_history = self._build_conversation_history(context.recent_messages)
            
            # Create the system prompt
            system_prompt = self._create_therapy_system_prompt(context)
            
            # Build the user message with context
            user_prompt = self._build_user_prompt(user_message, context)
            
            # Generate response from OpenAI
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *conversation_history,
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"}
            )
            
            # Parse the response
            response_content = response.choices[0].message.content
            parsed_response = json.loads(response_content)
            
            # Extract token usage if available
            usage_meta: Dict[str, Any] = {}
            try:
                if hasattr(response, "usage") and response.usage is not None:
                    usage_meta = {
                        "tokens_total": getattr(response.usage, "total_tokens", None),
                        "tokens_prompt": getattr(response.usage, "prompt_tokens", None),
                        "tokens_completion": getattr(response.usage, "completion_tokens", None),
                        "llm_model": self.model,
                        "provider": "openai",
                    }
            except Exception:
                pass

            # Create therapy response
            therapy_response = TherapyResponse(
                message=parsed_response.get("message", "I'm here to help you."),
                agent_type=context.agent_type,
                conversation_id=context.conversation_id,
                timestamp=datetime.now(timezone.utc),
                therapeutic_approach=parsed_response.get("therapeutic_approach", "supportive"),
                emotional_tone=parsed_response.get("emotional_tone", "empathetic"),
                follow_up_suggestions=parsed_response.get("follow_up_suggestions", []),
                crisis_detected=parsed_response.get("crisis_detected", False),
                metadata={**parsed_response.get("metadata", {}), **({"usage": usage_meta} if usage_meta else {}), "llm_model": self.model}
            )
            
            logger.info(f"Generated therapy response: {therapy_response.therapeutic_approach} approach")
            return therapy_response
            
        except Exception as e:
            logger.error(f"Error generating therapy response: {e}", exc_info=True)
            # Fallback to safe response
            return self._create_fallback_response(context, user_message)

    def _create_therapy_system_prompt(self, context: AgentContext) -> str:
        """Create the system prompt for the therapy agent"""
        base_prompt = f"""You are a professional {context.agent_type} AI assistant. Your role is to provide empathetic, supportive, and evidence-based therapeutic guidance.

IMPORTANT RULES:
1. Always respond in a warm, empathetic, and professional manner
2. Never give medical advice or diagnose conditions
3. If you detect crisis indicators, respond with urgency and provide crisis resources
4. Use therapeutic techniques appropriate for the {context.agent_type} context
5. Keep responses concise but meaningful (2-3 sentences)
6. Always respond in JSON format with the following structure:
{{
    "message": "Your therapeutic response here",
    "therapeutic_approach": "supportive|cognitive|mindfulness|crisis",
    "emotional_tone": "empathetic|encouraging|calming|urgent",
    "follow_up_suggestions": ["suggestion1", "suggestion2"],
    "crisis_detected": false,
    "metadata": {{"reasoning": "brief explanation"}}
}}

User Profile: {json.dumps(context.user_profile, default=str)}
Current Emotional State: {context.emotional_state or "unknown"}
Session Duration: {context.session_duration or 0} minutes

Crisis Indicators to Watch For:
- Suicidal thoughts or self-harm
- Violence towards others
- Severe panic attacks
- Acute psychosis symptoms
- Substance abuse emergencies

If crisis is detected, set crisis_detected to true and use urgent tone."""

        return base_prompt

    def _build_conversation_history(self, messages: List[Message]) -> List[Dict[str, str]]:
        """Build conversation history for context"""
        history = []
        
        for msg in messages[-6:]:  # Last 6 messages for context
            role = "assistant" if msg.message_type == "assistant" else "user"
            history.append({
                "role": role,
                "content": msg.content
            })
        
        return history

    def _build_user_prompt(self, user_message: str, context: AgentContext) -> str:
        """Build the user prompt with context"""
        prompt = f"User message: {user_message}\n\n"
        
        if context.crisis_indicators:
            prompt += f"⚠️ Crisis indicators detected: {', '.join(context.crisis_indicators)}\n\n"
        
        prompt += "Please provide a therapeutic response based on the context above."
        return prompt

    def _create_fallback_response(self, context: AgentContext, user_message: str) -> TherapyResponse:
        """Create a fallback response when LLM fails"""
        return TherapyResponse(
            message="I'm here to listen and support you. I'm experiencing some technical difficulties right now, but I want you to know that your feelings are valid and important. Please continue sharing, and I'll do my best to help.",
            agent_type=context.agent_type,
            conversation_id=context.agent_type,
            timestamp=datetime.now(timezone.utc),
            therapeutic_approach="supportive",
            emotional_tone="empathetic",
            follow_up_suggestions=["Try to express your feelings", "Consider what might help you feel better"],
            crisis_detected=False,
            metadata={"fallback": True, "error": "LLM service unavailable"}
        )

    async def analyze_emotional_state(self, message: str) -> Dict[str, Any]:
        """Analyze the emotional content of a message"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Analyze the emotional content of this message. Return JSON with: emotion (primary emotion), intensity (1-10), sentiment (positive/negative/neutral), crisis_indicators (list of concerning signs)."
                    },
                    {
                        "role": "user",
                        "content": message
                    }
                ],
                temperature=0.3,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error analyzing emotional state: {e}")
            return {
                "emotion": "neutral",
                "intensity": 5,
                "sentiment": "neutral",
                "crisis_indicators": []
            }

    async def health_check(self) -> bool:
        """Check if the LLM service is healthy"""
        try:
            await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return False
