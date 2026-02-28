"""Redis Event Bus Service Implementation

Publishes domain events to Redis Pub/Sub and dispatches to local handlers.
"""

import json
import logging
from typing import Callable, Any, List
from uuid import UUID

import redis.asyncio as aioredis

from ...application.services.event_bus import IEventBus
from ...domain.events.domain_events import DomainEvent

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "emotionai:events:"


class RedisEventBus(IEventBus):
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.handlers: dict[str, list[Callable]] = {}
        self._redis: aioredis.Redis | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        try:
            self._redis = aioredis.from_url(
                self.redis_url, decode_responses=True
            )
            await self._redis.ping()
            logger.info("Redis event bus connected")
        except Exception as exc:
            logger.warning(f"Redis event bus failed to connect: {exc}")
            self._redis = None

    async def stop(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("Redis event bus disconnected")

    # ------------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------------

    async def publish(self, event: DomainEvent) -> None:
        payload = json.dumps(event.to_dict(), default=str)
        channel = f"{CHANNEL_PREFIX}{event.event_type}"

        # Dispatch to local in-process handlers
        for handler in self.handlers.get(event.event_type, []):
            try:
                await handler(event)
            except Exception as exc:
                logger.error(f"Handler error for {event.event_type}: {exc}")

        # Publish to Redis if available
        if self._redis is not None:
            try:
                await self._redis.publish(channel, payload)
            except Exception as exc:
                logger.warning(f"Redis publish failed for {event.event_type}: {exc}")

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)

    # ------------------------------------------------------------------
    # Subscribe / Unsubscribe
    # ------------------------------------------------------------------

    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], Any]) -> None:
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[DomainEvent], Any]) -> None:
        if event_type in self.handlers:
            self.handlers[event_type].remove(handler)

    # ------------------------------------------------------------------
    # Health / Pending
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        if self._redis is None:
            return False
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False

    async def get_pending_events(self, user_id: UUID) -> List[DomainEvent]:
        # Pending-event persistence is not yet implemented.
        return []

    async def mark_event_processed(self, event_id: str) -> None:
        pass
