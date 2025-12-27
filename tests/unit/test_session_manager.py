"""Unit tests for session manager."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

try:
    from tidal_api.session_manager import SessionManager
except ImportError:
    import sys
    from pathlib import Path as PathLib

    sys.path.insert(0, str(PathLib(__file__).parent.parent.parent))
    from tidal_api.session_manager import SessionManager


@pytest.mark.unit
class TestSessionManager:
    """Test SessionManager class."""

    def test_get_session_file_path(self):
        """Test getting session file path."""
        manager = SessionManager()
        path = manager.get_session_file_path()
        assert isinstance(path, Path)
        assert path.name == "default.json"  # Changed to default.json for per-user sessions

    @patch("tidal_api.session_manager.BrowserSession")
    @patch("tidal_api.session_manager.Path.exists")
    def test_get_authenticated_session_success(self, mock_exists, mock_browser_session):
        """Test successful authentication."""
        mock_exists.return_value = True
        mock_session = Mock()
        mock_session.login_session_file_auto.return_value = True
        mock_session.user = Mock()
        mock_browser_session.return_value = mock_session

        manager = SessionManager()
        session = manager.get_authenticated_session()

        assert session == mock_session
        mock_session.login_session_file_auto.assert_called_once()

    @patch("tidal_api.session_manager.Path.exists")
    def test_get_authenticated_session_no_file(self, mock_exists):
        """Test authentication failure when session file doesn't exist."""
        mock_exists.return_value = False

        manager = SessionManager()
        with pytest.raises(RuntimeError, match="Not authenticated"):
            manager.get_authenticated_session()

    @patch("tidal_api.session_manager.BrowserSession")
    @patch("tidal_api.session_manager.Path.exists")
    def test_authenticate_success(self, mock_exists, mock_browser_session):
        """Test successful authentication (non-blocking flow)."""
        mock_exists.return_value = False
        mock_session = Mock()
        # Mock the new non-blocking login flow
        mock_session.start_oauth_login.return_value = ("https://auth.url", 300, Mock())
        mock_session.check_login.return_value = False  # Not logged in yet
        mock_browser_session.return_value = mock_session

        manager = SessionManager()
        result = manager.authenticate()

        # Now returns pending status with auth_url
        assert result["status"] == "pending"
        assert "auth_url" in result
        assert "session_id" in result
        assert "expires_in" in result

    @patch("tidal_api.session_manager.BrowserSession")
    @patch("tidal_api.session_manager.Path.exists")
    def test_authenticate_failure(self, mock_exists, mock_browser_session):
        """Test authentication failure."""
        mock_exists.return_value = False
        mock_session = Mock()
        mock_session.login_session_file_auto.return_value = False
        mock_browser_session.return_value = mock_session

        manager = SessionManager()
        result = manager.authenticate()

        assert result["status"] == "error"

    @patch("tidal_api.session_manager.BrowserSession")
    @patch("tidal_api.session_manager.Path.exists")
    def test_check_authentication_status_authenticated(self, mock_exists, mock_browser_session):
        """Test checking authentication status when authenticated."""
        mock_exists.return_value = True
        mock_session = Mock()
        mock_session.login_session_file_auto.return_value = True
        mock_session.user = Mock()
        mock_session.user.id = "12345"
        mock_session.user.username = "testuser"
        mock_session.user.email = "test@example.com"
        mock_browser_session.return_value = mock_session

        manager = SessionManager()
        result = manager.check_authentication_status()

        assert result["authenticated"] is True
        assert result["user"]["id"] == "12345"

    @patch("tidal_api.session_manager.Path.exists")
    def test_check_authentication_status_not_authenticated(self, mock_exists):
        """Test checking authentication status when not authenticated."""
        mock_exists.return_value = False

        manager = SessionManager()
        result = manager.check_authentication_status()

        assert result["authenticated"] is False
