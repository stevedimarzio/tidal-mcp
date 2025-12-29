"""
TIDAL session management.

Handles authentication and session lifecycle for TIDAL API access.
Supports per-user sessions for cloud deployment using DiskStore.
"""

import os
import threading
import uuid
from pathlib import Path

try:
    from .browser_session import BrowserSession
    from .logger import logger
    from .session_storage import SessionStorage
except ImportError:
    from browser_session import BrowserSession
    from logger import logger
    from session_storage import SessionStorage


class SessionManager:
    """Manages TIDAL authentication and session lifecycle with per-user session support."""

    def __init__(self, storage: SessionStorage | None = None):
        """
        Initialize session manager with DiskStore storage.

        Args:
            storage: Optional SessionStorage instance. If None, creates default storage.
        """
        self._pending_logins: dict[str, tuple] = {}  # session_id -> (future, expires_in, session)
        self._lock = threading.Lock()

        # Initialize storage
        if storage:
            self._storage = storage
        else:
            # Default storage initialization
            directory = self._get_storage_directory()
            self._storage = SessionStorage(directory=directory)

    def _get_storage_directory(self) -> str:
        """Get storage directory path."""
        home_dir = os.path.expanduser("~")
        config_dir = os.path.join(home_dir, ".tidal-mcp", "sessions")
        os.makedirs(config_dir, exist_ok=True, mode=0o700)
        return config_dir

    def get_authenticated_session(self, session_id: str | None = None) -> BrowserSession:
        """
        Get an authenticated TIDAL session for a specific user.

        Args:
            session_id: Optional session ID. If None, checks TIDAL_USER_ID environment variable.

        Returns:
            Authenticated BrowserSession instance

        Raises:
            RuntimeError: If authentication fails or session cannot be loaded
        """
        if not session_id:
            # Check environment variable
            env_user_id = os.getenv("TIDAL_USER_ID")
            if env_user_id:
                session_id = env_user_id
            else:
                raise RuntimeError("No session_id provided and TIDAL_USER_ID not set")

        # Load from DiskStore
        session_data = self._storage.load_session_sync(session_id)
        if not session_data:
            raise RuntimeError("Not authenticated. Please login first.")

        # Create session and load data
        session = BrowserSession()
        success = session.load_from_data(session_data)

        if not success or not session.check_login():
            raise RuntimeError("Authentication failed. Please login again.")

        return session

    def authenticate(self, session_id: str | None = None) -> dict:
        """
        Start TIDAL authentication flow and return auth URL immediately (non-blocking).

        Args:
            session_id: Optional session ID. If None, checks TIDAL_USER_ID environment
                       variable. If not set, generates a new UUID.

        Returns:
            Dictionary with auth_url, session_id, expires_in, and status
        """
        if not session_id:
            # Check for environment variable for user-specific default session
            env_user_id = os.getenv("TIDAL_USER_ID")
            if env_user_id:
                session_id = env_user_id
            else:
                session_id = str(uuid.uuid4())

        session = BrowserSession()

        # Try to load existing session first
        session_data = self._storage.load_session_sync(session_id)
        if session_data:
            try:
                success = session.load_from_data(session_data)
                if success and session.check_login():
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

            # Store pending login for status checking (REMOVE session_file from tuple)
            with self._lock:
                self._pending_logins[session_id] = (future, expires_in, session)

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
        # Check if login is pending
        with self._lock:
            if session_id in self._pending_logins:
                future, expires_in, session = self._pending_logins[session_id]

                # Check if login completed
                if future.done():
                    try:
                        future.result(timeout=0)  # Check immediately, don't wait
                        # Login completed successfully - verify session is valid
                        if session.check_login():
                            # Extract session data and save to DiskStore
                            session_data = session.get_session_data()
                            self._storage.save_session_sync(session_id, session_data)

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
                    # Note: We don't track start time, so we can't check expiration here
                    # The OAuth flow itself will timeout
                    return {
                        "status": "pending",
                        "authenticated": False,
                        "message": "Authentication in progress",
                        "session_id": session_id,
                        "expires_in": expires_in,
                    }

        # Check existing session in DiskStore
        session_data = self._storage.load_session_sync(session_id)
        if session_data:
            try:
                session = BrowserSession()
                success = session.load_from_data(session_data)

                if success and session.check_login() and session.user:
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

    def check_authentication_status(self, session_id: str | None = None) -> dict:
        """
        Check if there's an active authenticated session.

        Args:
            session_id: Optional session ID. If None, checks TIDAL_USER_ID environment variable.

        Returns:
            Dictionary with authentication status and user information
        """
        if session_id:
            return self.check_login_status(session_id)

        # Check environment variable
        env_user_id = os.getenv("TIDAL_USER_ID")
        if not env_user_id:
            return {"authenticated": False, "message": "No session_id provided and TIDAL_USER_ID not set"}

        session_data = self._storage.load_session_sync(env_user_id)
        if not session_data:
            return {"authenticated": False, "message": "No session found"}

        session = BrowserSession()
        success = session.load_from_data(session_data)

        if success and session.check_login() and session.user:
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

    def list_active_sessions(self) -> list[dict]:
        """
        List all active sessions from DiskStore.

        Returns:
            List of dictionaries containing session information:
            - session_id: The session identifier
            - authenticated: Whether the session is currently authenticated
            - user_info: User information if authenticated, None otherwise
        """
        session_ids = self._storage.list_sessions_sync()
        sessions = []

        for session_id in session_ids:
            try:
                # Load session data
                session_data = self._storage.load_session_sync(session_id)
                if not session_data:
                    continue

                # Try to validate session
                authenticated = False
                user_info = None
                try:
                    session = BrowserSession()
                    success = session.load_from_data(session_data)
                    if success and session.check_login() and session.user:
                        authenticated = True
                        user_info = {
                            "id": str(session.user.id),
                            "username": getattr(session.user, "username", None) or "N/A",
                            "email": getattr(session.user, "email", None) or "N/A",
                        }
                except Exception as e:
                    logger.debug(f"Could not validate session {session_id}: {e}")

                sessions.append({
                    "session_id": session_id,
                    "authenticated": authenticated,
                    "user_info": user_info,
                })
            except Exception as e:
                logger.warning(f"Error reading session {session_id}: {e}")
                continue

        return sessions

    def get_session_info(self, session_id: str) -> dict:
        """
        Get detailed information about a specific session.

        Args:
            session_id: The session ID to get information for

        Returns:
            Dictionary containing:
            - session_id: The session identifier
            - exists: Whether the session exists in DiskStore
            - authenticated: Whether the session is currently authenticated
            - user_info: User information if authenticated
            - is_pending: Whether there's a pending login for this session
        """
        result = {
            "session_id": session_id,
            "exists": False,
            "authenticated": False,
            "user_info": None,
            "is_pending": False,
        }

        # Check if login is pending
        with self._lock:
            if session_id in self._pending_logins:
                result["is_pending"] = True
                future, expires_in, _ = self._pending_logins[session_id]  # No file_path
                result["pending_status"] = "completed" if future.done() else "in_progress"

        # Check DiskStore
        session_data = self._storage.load_session_sync(session_id)
        if session_data:
            result["exists"] = True

            # Try to validate
            try:
                session = BrowserSession()
                success = session.load_from_data(session_data)
                if success and session.check_login() and session.user:
                    result["authenticated"] = True
                    result["user_info"] = {
                        "id": str(session.user.id),
                        "username": getattr(session.user, "username", None) or "N/A",
                        "email": getattr(session.user, "email", None) or "N/A",
                    }
            except Exception as e:
                logger.debug(f"Could not validate session {session_id}: {e}")

        return result
