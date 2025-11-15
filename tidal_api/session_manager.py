"""
TIDAL session management.

Handles authentication and session lifecycle for TIDAL API access.
"""

import os
import tempfile
from pathlib import Path

try:
    from .browser_session import BrowserSession
    from .logger import logger
except ImportError:
    from browser_session import BrowserSession
    from logger import logger


class SessionManager:
    """Manages TIDAL authentication and session lifecycle."""

    def get_session_file_path(self) -> Path:
        """Get the path to the TIDAL session file."""
        home_dir = os.path.expanduser("~")
        config_dir = os.path.join(home_dir, ".tidal-mcp")

        try:
            os.makedirs(config_dir, exist_ok=True, mode=0o700)
            return Path(config_dir) / "session.json"
        except (OSError, PermissionError):
            temp_dir = tempfile.gettempdir()
            return Path(temp_dir) / "tidal-session-oauth.json"

    def get_authenticated_session(self) -> BrowserSession:
        """
        Get an authenticated TIDAL session.

        Returns:
            Authenticated BrowserSession instance

        Raises:
            RuntimeError: If authentication fails or session cannot be loaded
        """
        session_file = self.get_session_file_path()

        if not session_file.exists():
            raise RuntimeError("Not authenticated. Please login first.")

        session = BrowserSession()
        login_success = session.login_session_file_auto(
            session_file, fn_print=lambda msg: logger.info(f"TIDAL AUTH: {msg}")
        )

        if not login_success:
            raise RuntimeError("Authentication failed. Please login again.")

        return session

    def authenticate(self) -> dict:
        """
        Authenticate with TIDAL through browser login flow.

        Returns:
            Dictionary with authentication status and user information
        """
        session_file = self.get_session_file_path()
        session = BrowserSession()

        def log_message(msg: str) -> None:
            logger.info(f"TIDAL AUTH: {msg}")

        try:
            login_success = session.login_session_file_auto(session_file, fn_print=log_message)

            if login_success:
                return {
                    "status": "success",
                    "message": "Successfully authenticated with TIDAL",
                    "user_id": str(session.user.id) if session.user else None,
                }
            else:
                return {"status": "error", "message": "Authentication failed"}

        except TimeoutError:
            return {
                "status": "error",
                "message": "Authentication timed out. Please try again.",
            }
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return {"status": "error", "message": f"Authentication error: {str(e)}"}

    def check_authentication_status(self) -> dict:
        """
        Check if there's an active authenticated session.

        Returns:
            Dictionary with authentication status and user information
        """
        session_file = self.get_session_file_path()

        if not session_file.exists():
            return {"authenticated": False, "message": "No session file found"}

        session = BrowserSession()
        login_success = session.login_session_file_auto(
            session_file, fn_print=lambda msg: logger.debug(f"TIDAL AUTH: {msg}")
        )

        if login_success:
            user_info = {
                "id": str(session.user.id),
                "username": getattr(session.user, "username", None) or "N/A",
                "email": getattr(session.user, "email", None) or "N/A",
            }

            return {
                "authenticated": True,
                "message": "Valid TIDAL session",
                "user": user_info,
            }
        else:
            return {"authenticated": False, "message": "Invalid or expired session"}


# Global instance for backward compatibility
_session_manager = SessionManager()


def get_session_file_path() -> Path:
    """Get the path to the TIDAL session file (backward compatibility)."""
    return _session_manager.get_session_file_path()


def get_authenticated_session() -> BrowserSession:
    """Get an authenticated TIDAL session (backward compatibility)."""
    return _session_manager.get_authenticated_session()


def authenticate() -> dict:
    """Authenticate with TIDAL through browser login flow (backward compatibility)."""
    return _session_manager.authenticate()


def check_authentication_status() -> dict:
    """Check if there's an active authenticated session (backward compatibility)."""
    return _session_manager.check_authentication_status()
