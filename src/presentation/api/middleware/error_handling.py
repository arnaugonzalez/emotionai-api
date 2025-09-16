"""
Error Handling Middleware

Provides centralized error handling and logging.
"""

import logging
from typing import Callable

from fastapi import Request, Response
from src.infrastructure.config.settings import settings
from src.infrastructure.observability.cloudwatch_logger import CloudWatchLogger
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle and log errors"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with error handling"""
        
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            logger.error(f"Unhandled error in {request.method} {request.url}: {str(e)}", exc_info=True)
            # Best-effort backend error logging to CloudWatch when enabled
            if settings.mobile_logs_enabled:
                try:
                    request_id = request.headers.get("X-Request-ID")
                    user = getattr(request.state, 'user', None)
                    email = None
                    if user and isinstance(user, dict):
                        email = user.get('email')
                    user_hash = ''
                    if email:
                        import hashlib
                        user_hash = hashlib.sha256(email.encode()).hexdigest()[:12]
                    cw = CloudWatchLogger()
                    cw.put_events(user_hash, [{
                        'event': 'backend.error',
                        'path': str(request.url.path),
                        'method': request.method,
                        'status': 500,
                        'error_class': e.__class__.__name__,
                        'message': str(e)[:500],
                        'request_id': request_id,
                    }])
                except Exception:
                    pass

            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An internal server error occurred"
                }
            ) 