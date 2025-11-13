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
    MCP_HTTP_PORT: Port for the MCP HTTP server (default: 8100)
    TIDAL_MCP_PORT: Port for the FastAPI backend (default: 5050)
"""
import sys
import os
import argparse
from pathlib import Path

# Add current directory to Python path
sys.path.append('.')

# Check if required modules are available
try:
    from mcp.server.fastmcp import FastMCP
    import uvicorn
except ImportError:
    print("ERROR: Required dependencies are not installed.", file=sys.stderr)
    print("\nThis project uses 'uv' for dependency management.", file=sys.stderr)
    print("Please run this script using:", file=sys.stderr)
    print("  uv run python start_mcp_http.py\n", file=sys.stderr)
    sys.exit(1)

# Import the MCP server
from mcp_server.server import mcp
from mcp_server.logger import logger


def main():
    parser = argparse.ArgumentParser(description="Start TIDAL MCP server in HTTP mode")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_HTTP_PORT", 8100)),
        help="Port for the MCP HTTP server (default: 8100)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)"
    )
    
    args = parser.parse_args()
    
    logger.info(f'Starting TIDAL MCP server in HTTP mode on {args.host}:{args.port}...')
    logger.info(f'FastAPI backend will run on port {os.environ.get("TIDAL_MCP_PORT", 5050)}')
    logger.info(f'Connect Cursor to: http://{args.host}:{args.port}/sse')
    logger.info('Press Ctrl+C to stop the server')
    
    # Set the port environment variable for the SSE transport
    os.environ["MCP_HTTP_PORT"] = str(args.port)
    
    # FastMCP supports SSE transport for HTTP mode
    # Use sse_app() to get the FastAPI app and run it with uvicorn
    try:
        # Get the FastAPI app from FastMCP for SSE transport
        app = mcp.sse_app()
        
        # Run with uvicorn on the specified host and port
        logger.info(f"Starting HTTP server on http://{args.host}:{args.port}")
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Failed to start HTTP server: {e}")
        import traceback
        traceback.print_exc()
        logger.info("Falling back to stdio mode...")
        # Fallback to stdio if HTTP fails
        mcp.run()


if __name__ == "__main__":
    main()

