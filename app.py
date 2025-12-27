"""
ASGI application entrypoint for TIDAL MCP server.

This module provides the HTTP server setup for the MCP server with:
- Health check endpoint (/health) via @mcp.custom_route()
- X-API-KEY header authentication middleware

Run with: uvicorn app:app --host 0.0.0.0 --port 8080 --forwarded-allow-ips=*
"""

import os

from mcp_server.logger import logger
from mcp_server.server import mcp
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Get API key from environment variable
api_key = os.environ.get("API_KEY")


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate X-API-KEY header."""

    async def dispatch(self, request: Request, call_next):
        # Skip API key check for health endpoint
        if request.url.path == "/health":
            return await call_next(request)

        # Skip if no API key is configured
        if not api_key:
            return await call_next(request)

        # Check for X-API-KEY header (case-insensitive)
        provided_key = request.headers.get("X-API-KEY") or request.headers.get("x-api-key")
        if not provided_key:
            client_host = request.client.host if request.client else "unknown"
            logger.warning(f"API key missing for request to {request.url.path} from {client_host}")
            return JSONResponse({"error": "Missing X-API-KEY header"}, status_code=401)

        if provided_key != api_key:
            client_host = request.client.host if request.client else "unknown"
            logger.warning(f"Invalid API key for request to {request.url.path} from {client_host}")
            return JSONResponse({"error": "Invalid API key"}, status_code=403)

        return await call_next(request)


# Configure middleware for API key authentication
# Health check route is defined in server.py via @mcp.custom_route()
if api_key:
    middleware = [Middleware(APIKeyMiddleware)]
    logger.info("X-API-KEY authentication enabled")
    app = mcp.http_app(middleware=middleware)
else:
    logger.warning("API_KEY environment variable not set - authentication disabled")
    app = mcp.http_app()


