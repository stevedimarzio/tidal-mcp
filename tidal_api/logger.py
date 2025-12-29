"""
Logging configuration for TIDAL MCP API.
Logs are written to stderr to avoid interfering with MCP's stdout communication.

This module re-exports the logger from mcp_server.logger for consistency.
"""

# Import from the consolidated logger module
import sys
from pathlib import Path

# Handle import for both module and direct execution
try:
    from ..mcp_server.logger import logger
except (ImportError, ValueError):
    # Fallback for direct execution - add parent directory to path
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from mcp_server.logger import logger

# Re-export logger for use in tidal_api module
__all__ = ["logger"]
