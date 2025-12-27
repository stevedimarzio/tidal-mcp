"""Interfaces and protocols for dependency injection."""

from pathlib import Path
from typing import Protocol

try:
    from .browser_session import BrowserSession
except ImportError:
    from browser_session import BrowserSession


class ISessionManager(Protocol):
    """Protocol for session management."""

    def get_authenticated_session(self, session_id: str | None = None) -> BrowserSession:
        """Get an authenticated TIDAL session for a specific user."""
        ...

    def authenticate(self) -> dict:
        """Authenticate with TIDAL through browser login flow."""
        ...

    def check_authentication_status(self) -> dict:
        """Check if there's an active authenticated session."""
        ...

    def get_session_file_path(self) -> Path:
        """Get the path to the TIDAL session file."""
        ...
