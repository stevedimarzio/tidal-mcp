"""
TIDAL session management.

Handles authentication and session lifecycle for TIDAL API access.
Supports per-user sessions for cloud deployment.
"""

import os
import tempfile
import uuid
import threading
from pathlib import Path
from typing import Optional

try:
    from .browser_session import BrowserSession
    from .logger import logger
except ImportError:
    from browser_session import BrowserSession
    from logger import logger


class SessionManager:
    """Manages TIDAL authentication and session lifecycle with per-user session support."""

    def __init__(self):
        """Initialize session manager with pending logins storage."""
        self._pending_logins: dict[str, tuple] = {}  # session_id -> (future, expires_in, session_file)
        self._lock = threading.Lock()

    def _get_sessions_dir(self) -> Path:
        """Get the directory for storing user sessions."""
        # Use data/sessions directory if it exists, otherwise use ~/.tidal-mcp/sessions
        data_sessions = Path("data/sessions")
        if data_sessions.exists() and data_sessions.is_dir():
            return data_sessions
        
        home_dir = os.path.expanduser("~")
        config_dir = os.path.join(home_dir, ".tidal-mcp", "sessions")
        
        try:
            os.makedirs(config_dir, exist_ok=True, mode=0o700)
            return Path(config_dir)
        except (OSError, PermissionError):
            temp_dir = Path(tempfile.gettempdir()) / "tidal-mcp-sessions"
            os.makedirs(temp_dir, exist_ok=True, mode=0o700)
            return temp_dir

    def get_session_file_path(self, session_id: Optional[str] = None) -> Path:
        """
        Get the path to the TIDAL session file for a specific user session.
        
        Args:
            session_id: Optional session ID. If None, uses default session.
        
        Returns:
            Path to the session file
        """
        sessions_dir = self._get_sessions_dir()
        
        if session_id:
            # Per-user session file
            return sessions_dir / f"{session_id}.json"
        else:
            # Default/legacy session file
            return sessions_dir / "default.json"

    def get_authenticated_session(self, session_id: Optional[str] = None) -> BrowserSession:
        """
        Get an authenticated TIDAL session for a specific user.

        Args:
            session_id: Optional session ID. If None, uses default session.

        Returns:
            Authenticated BrowserSession instance

        Raises:
            RuntimeError: If authentication fails or session cannot be loaded
        """
        session_file = self.get_session_file_path(session_id)

        if not session_file.exists():
            raise RuntimeError("Not authenticated. Please login first.")

        session = BrowserSession()
        login_success = session.login_session_file_auto(
            session_file, fn_print=lambda msg: logger.info(f"TIDAL AUTH: {msg}")
        )

        if not login_success:
            raise RuntimeError("Authentication failed. Please login again.")

        return session

    def authenticate(self, session_id: Optional[str] = None) -> dict:
        """
        Start TIDAL authentication flow and return auth URL immediately (non-blocking).

        Args:
            session_id: Optional session ID. If None, generates a new one.

        Returns:
            Dictionary with auth_url, session_id, expires_in, and status
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        session_file = self.get_session_file_path(session_id)
        session = BrowserSession()

        # Try to load existing session first
        if session_file.exists():
            try:
                session.load_session_from_file(session_file)
                if session.check_login():
                    return {
                        "status": "success",
                        "message": "Already authenticated",
                        "session_id": session_id,
                        "user_id": str(session.user.id) if session.user else None,
                    }
            except Exception as e:
                logger.debug(f"Could not load existing session: {e}")

        # Start new OAuth flow (non-blocking)
        try:
            auth_url, expires_in, future = session.start_oauth_login()
            
            # Store pending login for status checking
            with self._lock:
                self._pending_logins[session_id] = (future, expires_in, session_file, session)
            
            logger.info(f"TIDAL AUTH: Started login flow for session {session_id}")
            
            return {
                "status": "pending",
                "message": "Please visit the URL to complete authentication",
                "auth_url": auth_url,
                "session_id": session_id,
                "expires_in": expires_in,
            }
        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            return {"status": "error", "message": f"Authentication error: {str(e)}"}

    def check_login_status(self, session_id: str) -> dict:
        """
        Check the status of a pending login or existing session.

        Args:
            session_id: The session ID to check

        Returns:
            Dictionary with authentication status
        """
        session_file = self.get_session_file_path(session_id)

        # Check if login is pending
        with self._lock:
            if session_id in self._pending_logins:
                future, expires_in, file_path, session = self._pending_logins[session_id]
                
                # Check if login completed
                if future.done():
                    try:
                        future.result(timeout=0)  # Check immediately, don't wait
                        # Login completed successfully - verify session is valid
                        if session.check_login():
                            # Save session to file
                            file_path.parent.mkdir(parents=True, exist_ok=True)
                            session.save_session_to_file(file_path)
                            
                            # Get user info
                            user_id = None
                            if session.user:
                                user_id = str(session.user.id)
                            
                            # Remove from pending
                            del self._pending_logins[session_id]
                            
                            return {
                                "status": "success",
                                "authenticated": True,
                                "message": "Authentication completed",
                                "session_id": session_id,
                                "user_id": user_id,
                            }
                        else:
                            # Future completed but session not valid
                            del self._pending_logins[session_id]
                            return {
                                "status": "error",
                                "authenticated": False,
                                "message": "Authentication failed - session not valid",
                            }
                    except Exception as e:
                        # Future completed with error
                        del self._pending_logins[session_id]
                        logger.error(f"Login future error: {e}", exc_info=True)
                        return {
                            "status": "error",
                            "authenticated": False,
                            "message": f"Authentication error: {str(e)}",
                        }
                else:
                    # Still pending - check if expired
                    import time
                    # Note: We don't track start time, so we can't check expiration here
                    # The OAuth flow itself will timeout
                    return {
                        "status": "pending",
                        "authenticated": False,
                        "message": "Authentication in progress",
                        "session_id": session_id,
                        "expires_in": expires_in,
                    }

        # Check existing session file
        if session_file.exists():
            try:
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
                        "status": "success",
                        "authenticated": True,
                        "message": "Valid TIDAL session",
                        "session_id": session_id,
                        "user": user_info,
                    }
            except Exception as e:
                logger.debug(f"Session check error: {e}")

        return {
            "status": "not_authenticated",
            "authenticated": False,
            "message": "No active session found",
        }

    def check_authentication_status(self, session_id: Optional[str] = None) -> dict:
        """
        Check if there's an active authenticated session.

        Args:
            session_id: Optional session ID. If None, checks default session.

        Returns:
            Dictionary with authentication status and user information
        """
        if session_id:
            return self.check_login_status(session_id)

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


def get_authenticated_session(session_id: str | None = None) -> BrowserSession:
    """Get an authenticated TIDAL session (backward compatibility)."""
    return _session_manager.get_authenticated_session(session_id)


def authenticate(session_id: str | None = None) -> dict:
    """Authenticate with TIDAL through browser login flow (backward compatibility)."""
    return _session_manager.authenticate(session_id)


def check_authentication_status(session_id: str | None = None) -> dict:
    """Check if there's an active authenticated session (backward compatibility)."""
    return _session_manager.check_authentication_status(session_id)
