"""
Simple in-process WebSocket event manager to broadcast calendar updates to clients.
"""

import asyncio
from typing import Set, Dict, Any

from fastapi import WebSocket


class CalendarEventManager:
    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)

    async def broadcast(self, event: Dict[str, Any]) -> None:
        # Best-effort broadcast; drop broken connections
        async with self._lock:
            to_remove: Set[WebSocket] = set()
            for ws in list(self._connections):
                try:
                    await ws.send_json(event)
                except Exception:
                    to_remove.add(ws)
            for ws in to_remove:
                try:
                    await ws.close()
                except Exception:
                    pass
                self._connections.discard(ws)



