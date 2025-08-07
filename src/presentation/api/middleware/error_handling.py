"""
Error Handling Middleware

Provides centralized error handling and logging.
"""

import logging
from typing import Callable

from fastapi import Request, Response
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
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "message": "An internal server error occurred"
                }
            ) 