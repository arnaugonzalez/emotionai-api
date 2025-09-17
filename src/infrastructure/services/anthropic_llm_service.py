"""
Anthropic LLM Service Implementation

Provides AI-powered therapeutic responses using Anthropic's Claude models.
Defaults to Claude Sonnet for consistent, high-quality responses.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from anthropic import AsyncAnthropic

from ...domain.chat.entities import AgentContext, TherapyResponse, Message
from ...application.services.llm_service import ILLMService

logger = logging.getLogger(__name__)


class AnthropicLLMService(ILLMService):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-latest"):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model
        logger.info(f"Anthropic LLM Service initialized with model: {model}")

    async def generate_therapy_response(
        self,
        context: AgentContext,
        user_message: str
    ) -> TherapyResponse:
        """Generate a therapeutic response using Anthropic Claude"""
        try:
            system_prompt = self._create_therapy_system_prompt(context)
            conversation_history = self._build_conversation_history(context.recent_messages)
            user_prompt = self._build_user_prompt(user_message, context)

            messages: List[Dict[str, Any]] = [
                {"role": "user", "content": system_prompt},
            ]
            # Append conversation history as alternating messages
            messages.extend(conversation_history)
            messages.append({"role": "user", "content": user_prompt})

            resp = await self.client.messages.create(
                model=self.model,
                max_tokens=700,
                temperature=0.7,
                system="You must respond in strict JSON only.",
                messages=messages,
            )

            # Anthropic returns a content list; we extract text segments and parse JSON
            content_text = "".join(
                [blk.text for blk in resp.content if getattr(blk, "type", None) == "text"]
            )
            try:
                parsed = json.loads(content_text)
            except Exception:
                logger.warning("Claude response not valid JSON; returning fallback", exc_info=True)
                return self._create_fallback_response(context, user_message)

            # Anthropic usage fields vary; attempt to extract if present
            usage_meta: Dict[str, Any] = {}
            try:
                if hasattr(resp, "usage") and resp.usage is not None:
                    # Claude recent SDKs expose input_tokens/output_tokens
                    usage_meta = {
                        "tokens_total": (
                            getattr(resp.usage, "input_tokens", 0)
                            + getattr(resp.usage, "output_tokens", 0)
                        ),
                        "tokens_prompt": getattr(resp.usage, "input_tokens", None),
                        "tokens_completion": getattr(resp.usage, "output_tokens", None),
                        "llm_model": self.model,
                        "provider": "anthropic",
                    }
            except Exception:
                pass

            return TherapyResponse(
                message=parsed.get("message", "I'm here to help you."),
                agent_type=context.agent_type,
                conversation_id=context.conversation_id,
                timestamp=datetime.now(timezone.utc),
                therapeutic_approach=parsed.get("therapeutic_approach", "supportive"),
                emotional_tone=parsed.get("emotional_tone", "empathetic"),
                follow_up_suggestions=parsed.get("follow_up_suggestions", []),
                crisis_detected=parsed.get("crisis_detected", False),
                metadata={**parsed.get("metadata", {}), **({"usage": usage_meta} if usage_meta else {}), "llm_model": self.model},
            )

        except Exception as e:
            logger.error(f"Error generating therapy response (Anthropic): {e}", exc_info=True)
            return self._create_fallback_response(context, user_message)

    async def analyze_emotional_state(self, message: str) -> Dict[str, Any]:
        """Basic emotional analysis using Claude; returns a simple structure."""
        try:
            prompt = (
                "Analyze the emotional tone of the following message and return JSON with "
                "fields: primary_emotion (string), intensity (1-10), notes (string).\n\n"
                f"Message: {message}"
            )
            resp = await self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.3,
                system="Return strict JSON only.",
                messages=[{"role": "user", "content": prompt}],
            )
            content_text = "".join(
                [blk.text for blk in resp.content if getattr(blk, "type", None) == "text"]
            )
            return json.loads(content_text)
        except Exception as e:
            logger.error(f"Emotional analysis failed: {e}", exc_info=True)
            return {"primary_emotion": "neutral", "intensity": 3, "notes": "fallback"}

    async def health_check(self) -> bool:
        try:
            # Lightweight check: model name presence implies config, optionally a quick noop call
            return bool(self.model)
        except Exception:
            return False

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
        history: List[Dict[str, str]] = []
        for msg in messages[-6:]:  # Last 6 messages for context
            role = "assistant" if msg.message_type == "assistant" else "user"
            history.append({"role": role, "content": msg.content})
        return history

    def _build_user_prompt(self, user_message: str, context: AgentContext) -> str:
        """Build the user prompt with context"""
        prompt = f"User message: {user_message}\n\n"
        if context.crisis_indicators:
            prompt += f"Crisis indicators detected: {', '.join(context.crisis_indicators)}\n\n"
        prompt += "Please provide a therapeutic response based on the context above."
        return prompt

    def _create_fallback_response(self, context: AgentContext, user_message: str) -> TherapyResponse:
        """Create a fallback response when LLM fails"""
        return TherapyResponse(
            message=(
                "I'm here to listen and support you. I'm experiencing some technical difficulties "
                "right now, but your feelings are valid and important. Please continue sharing, "
                "and I'll do my best to help."
            ),
            agent_type=context.agent_type,
            conversation_id=context.agent_type,
            timestamp=datetime.now(timezone.utc),
            therapeutic_approach="supportive",
            emotional_tone="empathetic",
            follow_up_suggestions=["Try to express your feelings", "Consider what might help you feel better"],
            crisis_detected=False,
            metadata={"fallback": True, "error": "LLM service unavailable"},
        )
