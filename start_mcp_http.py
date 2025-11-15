#!/usr/bin/env python3
"""
Start TIDAL MCP server in HTTP mode for debugging.

This script starts the MCP server in HTTP mode using SSE (Server-Sent Events) transport,
which allows you to:
- Debug the server using standard HTTP debugging tools
- Connect Cursor to the server via HTTP transport
- Monitor network traffic and requests

Usage:
    uv run python start_mcp_http.py [--port PORT] [--host HOST]

Environment variables:
    PORT: Port for the MCP HTTP server (CloudRun compatible, default: 8080)
    MCP_HTTP_PORT: Port for the MCP HTTP server (alternative to PORT, default: 8080)
"""

import argparse
import os
import sys

# Add current directory to Python path
sys.path.append(".")

# Check if required modules are available
try:
    import uvicorn
except ImportError:
    print("ERROR: Required dependencies are not installed.", file=sys.stderr)
    print("\nThis project uses 'uv' for dependency management.", file=sys.stderr)
    print("Please run this script using:", file=sys.stderr)
    print("  uv run python start_mcp_http.py\n", file=sys.stderr)
    sys.exit(1)

# Import the MCP server
from mcp_server.logger import logger
from mcp_server.server import mcp


def main():
    parser = argparse.ArgumentParser(description="Start TIDAL MCP server in HTTP mode")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("PORT", os.environ.get("MCP_HTTP_PORT", 8080))),
        help="Port for the MCP HTTP server (default: 8080, supports PORT env var for CloudRun)",
    )
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )

    args = parser.parse_args()

    logger.info(f"Starting TIDAL MCP server in HTTP mode on {args.host}:{args.port}...")
    logger.info(f"Connect Cursor to: http://{args.host}:{args.port}/sse")
    logger.info("Press Ctrl+C to stop the server")

    # Set the port environment variable for the SSE transport
    os.environ["MCP_HTTP_PORT"] = str(args.port)

    try:
        app = mcp.sse_app()

        # Add health check endpoint for cloud container services
        # FastMCP's sse_app() returns a Starlette app, not FastAPI
        from starlette.responses import JSONResponse

        @app.route("/health", methods=["GET"])
        async def health(request):
            """Health check endpoint for cloud container services"""
            return JSONResponse({"status": "healthy", "service": "tidal-mcp"})

        logger.info(f"Starting HTTP server on http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}")
        import traceback

        traceback.print_exc()
        logger.info("Falling back to stdio mode...")
        # Fallback to stdio if HTTP fails
        mcp.run()


if __name__ == "__main__":
    main()
