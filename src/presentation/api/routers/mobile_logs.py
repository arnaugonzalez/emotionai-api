from __future__ import annotations

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.presentation.dependencies import get_current_user_id
from src.infrastructure.config.settings import settings
from src.infrastructure.observability.cloudwatch_logger import CloudWatchLogger

router = APIRouter(redirect_slashes=False)


class MobileLogItem(BaseModel):
    ts_iso: Optional[str] = None
    level: str
    event: str
    user_hash: Optional[str] = None
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    online: Optional[bool] = None
    method: Optional[str] = None
    url: Optional[str] = None
    status: Optional[int] = None
    latency_ms: Optional[int] = Field(None, alias='latency_ms')
    queue_len: Optional[int] = None
    error: Optional[str] = None
    retry_count: Optional[int] = None
    sdk: Optional[str] = None
    app_ver: Optional[str] = None


@router.post("/mobile-logs", status_code=status.HTTP_204_NO_CONTENT)
async def ingest_mobile_logs(
    items: List[MobileLogItem],
    user_id: UUID = Depends(get_current_user_id),
):
    # Enforce body size and rate limit via upstream (left for middleware/nginx), keep minimal checks here
    if not items:
        return
    # No-op if disabled
    if not settings.mobile_logs_enabled:
        return
    # Derive user hash from user_id (no email dependency)
    import hashlib
    user_hash = hashlib.sha256(str(user_id).encode()).hexdigest()[:12]

    try:
        cw = CloudWatchLogger()
        payloads = [i.model_dump(by_alias=True) for i in items]
        cw.put_events(user_hash, payloads)
    except Exception:
        # Do not block app if logging fails
        return


