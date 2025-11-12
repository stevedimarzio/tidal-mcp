#!/usr/bin/env python3
"""
Simple startup script for TIDAL MCP server.

This script should be run with uv to ensure all dependencies are available:
    uv run python start_mcp.py

Or use uv directly:
    uv run mcp run mcp_server/server.py
"""
import sys
import os

# Add current directory to Python path
sys.path.append('.')

# Check if required modules are available
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: Required dependencies are not installed.", file=sys.stderr)
    print("\nThis project uses 'uv' for dependency management.", file=sys.stderr)
    print("Please run this script using one of the following methods:\n", file=sys.stderr)
    print("  1. uv run python start_mcp.py", file=sys.stderr)
    print("  2. uv run mcp run mcp_server/server.py\n", file=sys.stderr)
    print("Or install dependencies first:", file=sys.stderr)
    print("  uv pip install --editable .\n", file=sys.stderr)
    sys.exit(1)

# Import and run the MCP server
from mcp_server.server import mcp
from mcp_server.logger import logger

if __name__ == "__main__":
    logger.info('Starting TIDAL MCP server...')
    mcp.run()