"""Unit tests for session manager."""

from unittest.mock import Mock, patch

import pytest

try:
    from tidal_api.session_manager import SessionManager
    from tidal_api.session_storage import SessionStorage
except ImportError:
    import sys
    from pathlib import Path as PathLib

    sys.path.insert(0, str(PathLib(__file__).parent.parent.parent))
    from tidal_api.session_manager import SessionManager
    from tidal_api.session_storage import SessionStorage


@pytest.mark.unit
class TestSessionManager:
    """Test SessionManager class."""

    @patch("tidal_api.session_manager.BrowserSession")
    def test_get_authenticated_session_success(self, mock_browser_session):
        """Test successful authentication."""
        # Mock session data
        mock_session_data = {"token": "test_token", "user_id": "12345"}
        mock_session = Mock()
        mock_session.load_from_data.return_value = True
        mock_session.check_login.return_value = True
        mock_session.user = Mock()
        mock_browser_session.return_value = mock_session

        # Mock storage
        mock_storage = Mock(spec=SessionStorage)
        mock_storage.load_session_sync.return_value = mock_session_data

        manager = SessionManager(storage=mock_storage)
        session = manager.get_authenticated_session(session_id="test_session_id")

        assert session == mock_session
        mock_storage.load_session_sync.assert_called_once_with("test_session_id")
        mock_session.load_from_data.assert_called_once_with(mock_session_data)
        mock_session.check_login.assert_called_once()

    def test_get_authenticated_session_no_session_id(self):
        """Test authentication failure when no session_id provided."""
        mock_storage = Mock(spec=SessionStorage)
        manager = SessionManager(storage=mock_storage)

        with pytest.raises(RuntimeError, match="No session_id provided"):
            manager.get_authenticated_session()

    def test_get_authenticated_session_no_file(self):
        """Test authentication failure when session doesn't exist."""
        mock_storage = Mock(spec=SessionStorage)
        mock_storage.load_session_sync.return_value = None

        manager = SessionManager(storage=mock_storage)
        with pytest.raises(RuntimeError, match="Not authenticated"):
            manager.get_authenticated_session(session_id="nonexistent_session")

    @patch("tidal_api.session_manager.BrowserSession")
    def test_authenticate_success(self, mock_browser_session):
        """Test successful authentication (non-blocking flow)."""
        mock_session = Mock()
        # Mock the new non-blocking login flow
        mock_future = Mock()
        mock_session.start_oauth_login.return_value = ("https://auth.url", 300, mock_future)
        mock_session.check_login.return_value = False  # Not logged in yet
        mock_browser_session.return_value = mock_session

        # Mock storage - no existing session
        mock_storage = Mock(spec=SessionStorage)
        mock_storage.load_session_sync.return_value = None

        manager = SessionManager(storage=mock_storage)
        result = manager.authenticate(session_id="test_session_id")

        # Now returns pending status with auth_url
        assert result["status"] == "pending"
        assert "auth_url" in result
        assert result["session_id"] == "test_session_id"
        assert "expires_in" in result

    @patch("tidal_api.session_manager.BrowserSession")
    def test_authenticate_failure(self, mock_browser_session):
        """Test authentication failure."""
        mock_session = Mock()
        mock_session.start_oauth_login.side_effect = Exception("OAuth error")
        mock_browser_session.return_value = mock_session

        # Mock storage - no existing session
        mock_storage = Mock(spec=SessionStorage)
        mock_storage.load_session_sync.return_value = None

        manager = SessionManager(storage=mock_storage)
        result = manager.authenticate(session_id="test_session_id")

        assert result["status"] == "error"
        assert "error" in result["message"].lower()

    @patch("tidal_api.session_manager.BrowserSession")
    def test_check_authentication_status_authenticated(self, mock_browser_session):
        """Test checking authentication status when authenticated."""
        # Mock session data
        mock_session_data = {"token": "test_token", "user_id": "12345"}
        mock_session = Mock()
        mock_session.load_from_data.return_value = True
        mock_session.check_login.return_value = True
        mock_session.user = Mock()
        mock_session.user.id = "12345"
        mock_session.user.username = "testuser"
        mock_session.user.email = "test@example.com"
        mock_browser_session.return_value = mock_session

        # Mock storage
        mock_storage = Mock(spec=SessionStorage)
        mock_storage.load_session_sync.return_value = mock_session_data

        manager = SessionManager(storage=mock_storage)
        result = manager.check_authentication_status(session_id="test_session_id")

        assert result["authenticated"] is True
        assert result["user"]["id"] == "12345"

    def test_check_authentication_status_not_authenticated(self):
        """Test checking authentication status when not authenticated."""
        # Mock storage - no session found
        mock_storage = Mock(spec=SessionStorage)
        mock_storage.load_session_sync.return_value = None

        manager = SessionManager(storage=mock_storage)
        result = manager.check_authentication_status(session_id="nonexistent_session")

        assert result["authenticated"] is False

    def test_check_authentication_status_no_session_id(self):
        """Test checking authentication status when no session_id provided."""
        mock_storage = Mock(spec=SessionStorage)
        manager = SessionManager(storage=mock_storage)

        result = manager.check_authentication_status()

        assert result["authenticated"] is False
        assert "No session_id provided" in result["message"]
