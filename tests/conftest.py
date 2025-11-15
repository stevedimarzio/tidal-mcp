"""Pytest configuration and shared fixtures."""

from pathlib import Path
from unittest.mock import Mock

import pytest

try:
    from tidal_api.browser_session import BrowserSession
    from tidal_api.session_manager import SessionManager
except ImportError:
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    from tidal_api.browser_session import BrowserSession
    from tidal_api.session_manager import SessionManager


@pytest.fixture
def mock_session() -> Mock:
    """Create a mock TIDAL session."""
    session = Mock(spec=BrowserSession)
    session.user = Mock()
    session.user.id = "12345"
    session.user.favorites = Mock()
    session.user.playlists = Mock(return_value=[])
    session.user.create_playlist = Mock()
    session.check_login = Mock(return_value=True)
    session.track = Mock()
    session.playlist = Mock()
    session.search = Mock(return_value={})
    return session


@pytest.fixture
def mock_session_manager(mock_session: Mock) -> Mock:
    """Create a mock session manager."""
    manager = Mock(spec=SessionManager)
    manager.get_authenticated_session = Mock(return_value=mock_session)
    manager.authenticate = Mock(return_value={"status": "success", "user_id": "12345"})
    manager.check_authentication_status = Mock(
        return_value={"authenticated": True, "user": {"id": "12345"}}
    )
    return manager
