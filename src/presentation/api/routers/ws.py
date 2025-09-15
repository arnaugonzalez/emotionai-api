"""
WebSocket Router for real-time calendar updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from uuid import UUID
import jwt
from ....infrastructure.config.settings import settings

from ..events.manager import CalendarEventManager


router = APIRouter(redirect_slashes=False)
events = CalendarEventManager()


@router.websocket("/ws/calendar")
async def calendar_ws(websocket: WebSocket):
    # Expect token in query params (?token=...)
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    try:
        data = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if data.get("typ") != "access":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        sub = data.get("sub")
        _ = UUID(sub)  # validate UUID format
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await events.connect(websocket)
    try:
        while True:
            # keep alive; ignore client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        await events.disconnect(websocket)


async def broadcast_calendar_event(event_type: str, payload: dict):
    await events.broadcast({"type": event_type, "payload": payload})



