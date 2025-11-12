import subprocess
import os
import pathlib
import shutil
import sys
from pathlib import Path

# Handle logger import for both module and direct execution
try:
    from .logger import logger
except ImportError:
    # Fallback for direct execution - add parent directory to path
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from mcp_server.logger import logger

# Define a configurable port with a default that's less likely to conflict
DEFAULT_PORT = 5050
FASTAPI_PORT = int(os.environ.get("TIDAL_MCP_PORT", DEFAULT_PORT))

# Define the base URL for your FastAPI app using the configurable port
FASTAPI_APP_URL = f"http://127.0.0.1:{FASTAPI_PORT}"

# Define the path to the FastAPI app dynamically
CURRENT_DIR = pathlib.Path(__file__).parent.absolute()
FASTAPI_APP_PATH = os.path.join(CURRENT_DIR, "..", "tidal_api", "app.py")
FASTAPI_APP_PATH = os.path.normpath(FASTAPI_APP_PATH)  # Normalize the path

# Keep FLASK_APP_URL for backward compatibility during migration
FLASK_APP_URL = FASTAPI_APP_URL
FLASK_PORT = FASTAPI_PORT

# Find the path to uv executable
def find_uv_executable():
    """Find the uv executable in the path or common locations"""
    # First try to find in PATH
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    
    # Check common installation locations
    common_locations = [
        os.path.expanduser("~/.local/bin/uv"),  # Linux/macOS local install
        os.path.expanduser("~/AppData/Local/Programs/Python/Python*/Scripts/uv.exe"),  # Windows
        "/usr/local/bin/uv",  # macOS Homebrew
        "/opt/homebrew/bin/uv",  # macOS Apple Silicon Homebrew
    ]
    
    for location in common_locations:
        # Handle wildcards in paths
        if "*" in location:
            import glob
            matches = glob.glob(location)
            for match in matches:
                if os.path.isfile(match) and os.access(match, os.X_OK):
                    return match
        elif os.path.isfile(location) and os.access(location, os.X_OK):
            return location
    
    # If we can't find it, just return "uv" and let the system try to resolve it
    return "uv"

# Global variable to hold the FastAPI app process
fastapi_process = None

def start_fastapi_app():
    """Start the FastAPI app as a subprocess"""
    global fastapi_process
    
    logger.info("Starting TIDAL FastAPI app...")
    
    # Find uv executable
    uv_executable = find_uv_executable()
    logger.debug(f"Using uv executable: {uv_executable}")
    
    # Start the Flask app using uv
    # Include certifi to ensure SSL certificates are available
    flask_process = subprocess.Popen([
        uv_executable, "run",
        "--with", "tidalapi",
        "--with", "fastapi",
        "--with", "uvicorn",
        "--with", "requests",
        "python", FASTAPI_APP_PATH
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Optional: Read a few lines to ensure the app starts properly
    for _ in range(5):  # Read first 5 lines of output
        line = fastapi_process.stdout.readline()
        if line:
            logger.debug(f"FastAPI app: {line.decode().strip()}")
    
    logger.info("TIDAL FastAPI app started")

def shutdown_fastapi_app():
    """Shutdown the FastAPI app subprocess when the MCP server exits"""
    global fastapi_process
    
    if fastapi_process:
        logger.info("Shutting down TIDAL FastAPI app...")
        # Try to terminate gracefully first
        fastapi_process.terminate()
        try:
            # Wait up to 5 seconds for process to terminate
            fastapi_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # If it doesn't terminate in time, force kill it
            fastapi_process.kill()
        logger.info("TIDAL FastAPI app shutdown complete")
