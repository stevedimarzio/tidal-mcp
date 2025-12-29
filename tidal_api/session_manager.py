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
        # Use data/sessions directory if it exists (for Docker/cloud), otherwise use ~/.tidal-mcp/sessions
        data_sessions = Path("data/sessions")
        if data_sessions.exists() and data_sessions.is_dir():
            return data_sessions
        
        # Try to create data/sessions if we're in the app directory
        try:
            data_sessions.mkdir(parents=True, exist_ok=True, mode=0o700)
            if data_sessions.is_dir():
                return data_sessions
        except (OSError, PermissionError):
            pass
        
        # Fallback to home directory
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

    def _load_sessions_from_disk(self):
        """Load existing sessions from disk into memory on startup."""
        sessions_dir = self._get_sessions_dir()
        if not sessions_dir.exists():
            return
        
        loaded_count = 0
        for session_file in sessions_dir.glob("*.json"):
            try:
                session_id = session_file.stem
                session = BrowserSession()
                session.load_session_from_file(session_file)
                
                if session.check_login():
                    # Load into memory with 1h expiry
                    expires_at = time.time() + self.SESSION_EXPIRY_SECONDS
                    user_info = {
                        "id": str(session.user.id) if session.user else None,
                        "username": getattr(session.user, "username", None) or "N/A",
                        "email": getattr(session.user, "email", None) or "N/A",
                    }
                    
                    with self._lock:
                        self._sessions[session_id] = (session, expires_at, user_info)
                    loaded_count += 1
                    logger.info(f"Loaded session {session_id} from disk")
            except Exception as e:
                logger.debug(f"Could not load session from {session_file}: {e}")
        
        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} sessions from disk into memory")

    def _save_session_to_disk(self, session_id: str, session: BrowserSession):
        """Save session to disk as backup."""
        try:
            session_file = self.get_session_file_path(session_id)
            session_file.parent.mkdir(parents=True, exist_ok=True)
            session.save_session_to_file(session_file)
            logger.debug(f"Saved session {session_id} to disk")
        except Exception as e:
            logger.warning(f"Could not save session to disk: {e}")

    def _is_session_valid(self, session_id: str) -> bool:
        """Check if session exists and is not expired."""
        with self._lock:
            if session_id not in self._sessions:
                return False
            
            session, expires_at, _ = self._sessions[session_id]
            
            # Check expiry
            if time.time() > expires_at:
                logger.info(f"Session {session_id} expired, removing from memory")
                del self._sessions[session_id]
                return False
            
            # Verify session is still valid with TIDAL
            try:
                if not session.check_login():
                    logger.info(f"Session {session_id} invalid with TIDAL, removing")
                    del self._sessions[session_id]
                    return False
            except Exception as e:
                logger.warning(f"Error checking session validity: {e}")
                del self._sessions[session_id]
                return False
            
            return True

    def get_authenticated_session(self, session_id: Optional[str] = None) -> BrowserSession:
        """
        Get an authenticated TIDAL session for a specific user.
        Uses in-memory storage first, falls back to disk if needed.

        Args:
            session_id: Optional session ID. If None, uses default session.

        Returns:
            Authenticated BrowserSession instance

        Raises:
            RuntimeError: If authentication fails or session cannot be loaded
        """
        if not session_id:
            session_id = "default"
        
        # Check in-memory first
        with self._lock:
            if self._is_session_valid(session_id):
                session, expires_at, _ = self._sessions[session_id]
                # Extend expiry on use (refresh to 1h from now)
                expires_at = time.time() + self.SESSION_EXPIRY_SECONDS
                self._sessions[session_id] = (session, expires_at, self._sessions[session_id][2])
                return session
        
        # Fallback to disk
        session_file = self.get_session_file_path(session_id)
        if session_file.exists():
            try:
                session = BrowserSession()
                login_success = session.login_session_file_auto(
                    session_file, fn_print=lambda msg: logger.debug(f"TIDAL AUTH: {msg}")
                )
                
                if login_success:
                    # Load into memory
                    expires_at = time.time() + self.SESSION_EXPIRY_SECONDS
                    user_info = {
                        "id": str(session.user.id) if session.user else None,
                        "username": getattr(session.user, "username", None) or "N/A",
                        "email": getattr(session.user, "email", None) or "N/A",
                    }
                    
                    with self._lock:
                        self._sessions[session_id] = (session, expires_at, user_info)
                    
                    return session
            except Exception as e:
                logger.debug(f"Could not load session from disk: {e}")

        raise RuntimeError("Not authenticated. Please login first.")

    def authenticate(self, session_id: Optional[str] = None, callback_url: Optional[str] = None) -> dict:
        """
        Start TIDAL authentication flow and return auth URL immediately (non-blocking).

        Args:
            session_id: Optional session ID. If None, generates a new one.
            callback_url: Optional callback URL for redirect after login completion.

        Returns:
            Dictionary with auth_url, session_id, expires_in, and status
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        # Check if already authenticated in memory
        with self._lock:
            if self._is_session_valid(session_id):
                _, _, user_info = self._sessions[session_id]
                return {
                    "status": "success",
                    "message": "Already authenticated",
                    "session_id": session_id,
                    "user_id": user_info.get("id"),
                }

        session_file = self.get_session_file_path(session_id)
        session = BrowserSession()

        # Try to load existing session from disk
        if session_file.exists():
            try:
                session.load_session_from_file(session_file)
                if session.check_login():
                    # Load into memory
                    expires_at = time.time() + self.SESSION_EXPIRY_SECONDS
                    user_info = {
                        "id": str(session.user.id) if session.user else None,
                        "username": getattr(session.user, "username", None) or "N/A",
                        "email": getattr(session.user, "email", None) or "N/A",
                    }
                    
                    with self._lock:
                        self._sessions[session_id] = (session, expires_at, user_info)
                    
                    return {
                        "status": "success",
                        "message": "Already authenticated",
                        "session_id": session_id,
                        "user_id": user_info.get("id"),
                    }
            except Exception as e:
                logger.debug(f"Could not load existing session: {e}")

        # Start new OAuth flow (non-blocking)
        try:
            auth_url, expires_in, future = session.start_oauth_login()
            
            # Store callback URL if provided
            if callback_url:
                with self._lock:
                    self._callbacks[session_id] = callback_url
            
            # Store pending login for status checking
            created_at = time.time()
            with self._lock:
                self._pending_logins[session_id] = (future, expires_in, session_file, session, created_at)
            
            logger.info(f"TIDAL AUTH: Started login flow for session {session_id}")
            
            return {
                "status": "pending",
                "message": "Please visit the URL to complete authentication",
                "auth_url": auth_url,
                "session_id": session_id,
                "expires_in": expires_in,
                "callback_url": callback_url,  # Echo back for client reference
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
            Dictionary with authentication status and callback_url if available
        """
        # Check in-memory session first
        with self._lock:
            if self._is_session_valid(session_id):
                _, _, user_info = self._sessions[session_id]
                callback_url = self._callbacks.get(session_id)
                result = {
                    "status": "success",
                    "authenticated": True,
                    "message": "Valid TIDAL session",
                    "session_id": session_id,
                    "user": user_info,
                }
                if callback_url:
                    result["callback_url"] = callback_url
                return result

        session_file = self.get_session_file_path(session_id)

        # Check if login is pending
        with self._lock:
            if session_id in self._pending_logins:
                future, expires_in, file_path, session, created_at = self._pending_logins[session_id]
                
                # Check if expired
                elapsed = time.time() - created_at
                if elapsed > expires_in:
                    logger.info(f"Login expired for session {session_id}")
                    del self._pending_logins[session_id]
                    if session_id in self._callbacks:
                        del self._callbacks[session_id]
                    return {
                        "status": "error",
                        "authenticated": False,
                        "message": "Authentication expired. Please try again.",
                    }
                
                # Check if login completed
                if future.done():
                    try:
                        future.result(timeout=0)  # Check immediately, don't wait
                        # Login completed successfully - verify session is valid
                        if session.check_login():
                            # Store in memory with 1h expiry
                            expires_at = time.time() + self.SESSION_EXPIRY_SECONDS
                            user_info = {
                                "id": str(session.user.id) if session.user else None,
                                "username": getattr(session.user, "username", None) or "N/A",
                                "email": getattr(session.user, "email", None) or "N/A",
                            }
                            
                            with self._lock:
                                self._sessions[session_id] = (session, expires_at, user_info)
                                callback_url = self._callbacks.pop(session_id, None)
                                del self._pending_logins[session_id]
                            
                            # Save to disk as backup
                            self._save_session_to_disk(session_id, session)
                            
                            result = {
                                "status": "success",
                                "authenticated": True,
                                "message": "Authentication completed",
                                "session_id": session_id,
                                "user": user_info,
                            }
                            if callback_url:
                                result["callback_url"] = callback_url
                            
                            logger.info(f"Authentication completed for session {session_id}")
                            return result
                        else:
                            # Future completed but session not valid
                            with self._lock:
                                del self._pending_logins[session_id]
                                if session_id in self._callbacks:
                                    del self._callbacks[session_id]
                            return {
                                "status": "error",
                                "authenticated": False,
                                "message": "Authentication failed - session not valid",
                            }
                    except Exception as e:
                        # Future completed with error
                        with self._lock:
                            del self._pending_logins[session_id]
                            if session_id in self._callbacks:
                                del self._callbacks[session_id]
                        logger.error(f"Login future error: {e}", exc_info=True)
                        return {
                            "status": "error",
                            "authenticated": False,
                            "message": f"Authentication error: {str(e)}",
                        }
                else:
                    # Still pending
                    callback_url = self._callbacks.get(session_id)
                    result = {
                        "status": "pending",
                        "authenticated": False,
                        "message": "Authentication in progress",
                        "session_id": session_id,
                        "expires_in": int(expires_in - elapsed),
                    }
                    if callback_url:
                        result["callback_url"] = callback_url
                    return result

        # Check existing session file (fallback)
        if session_file.exists():
            try:
                session = BrowserSession()
                login_success = session.login_session_file_auto(
                    session_file, fn_print=lambda msg: logger.debug(f"TIDAL AUTH: {msg}")
                )

                if login_success:
                    # Load into memory
                    expires_at = time.time() + self.SESSION_EXPIRY_SECONDS
                    user_info = {
                        "id": str(session.user.id),
                        "username": getattr(session.user, "username", None) or "N/A",
                        "email": getattr(session.user, "email", None) or "N/A",
                    }
                    
                    with self._lock:
                        self._sessions[session_id] = (session, expires_at, user_info)
                        callback_url = self._callbacks.get(session_id)
                    
                    result = {
                        "status": "success",
                        "authenticated": True,
                        "message": "Valid TIDAL session",
                        "session_id": session_id,
                        "user": user_info,
                    }
                    if callback_url:
                        result["callback_url"] = callback_url
                    return result
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
        Uses in-memory storage first for faster access.

        Args:
            session_id: Optional session ID. If None, checks default session.

        Returns:
            Dictionary with authentication status and user information
        """
        if session_id:
            return self.check_login_status(session_id)

        # Check default session in memory
        with self._lock:
            if self._is_session_valid("default"):
                _, _, user_info = self._sessions["default"]
                return {
                    "authenticated": True,
                    "message": "Valid TIDAL session",
                    "user": user_info,
                }

        # Fallback to disk
        session_file = self.get_session_file_path()

        if not session_file.exists():
            return {"authenticated": False, "message": "No session file found"}

        session = BrowserSession()
        login_success = session.login_session_file_auto(
            session_file, fn_print=lambda msg: logger.debug(f"TIDAL AUTH: {msg}")
        )

        if login_success:
            # Load into memory
            expires_at = time.time() + self.SESSION_EXPIRY_SECONDS
            user_info = {
                "id": str(session.user.id),
                "username": getattr(session.user, "username", None) or "N/A",
                "email": getattr(session.user, "email", None) or "N/A",
            }
            
            with self._lock:
                self._sessions["default"] = (session, expires_at, user_info)

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
