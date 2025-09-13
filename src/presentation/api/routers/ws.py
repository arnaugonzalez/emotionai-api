"""
WebSocket Router for real-time calendar updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..events.manager import CalendarEventManager


router = APIRouter(redirect_slashes=False)
events = CalendarEventManager()


@router.websocket("/ws/calendar")
async def calendar_ws(websocket: WebSocket):
    await events.connect(websocket)
    try:
        while True:
            # keep alive; ignore client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        await events.disconnect(websocket)


async def broadcast_calendar_event(event_type: str, payload: dict):
    await events.broadcast({"type": event_type, "payload": payload})



