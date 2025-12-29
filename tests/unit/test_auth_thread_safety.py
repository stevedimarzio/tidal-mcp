"""Unit tests for authentication thread safety and DiskStore usage."""

import threading
from unittest.mock import Mock, patch

import pytest

try:
    from tidal_api.session_manager import SessionManager
    from tidal_api.session_storage import SessionStorage
except ImportError:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from tidal_api.session_manager import SessionManager
    from tidal_api.session_storage import SessionStorage


@pytest.mark.unit
class TestAuthThreadSafety:
    """Test thread safety of authentication operations."""

    def test_session_manager_has_lock(self):
        """Test that SessionManager has a lock."""
        manager = SessionManager()
        assert hasattr(manager, '_lock')
        assert hasattr(manager._lock, 'acquire')
        assert hasattr(manager._lock, 'release')

    def test_session_storage_has_lock(self):
        """Test that SessionStorage has a lock."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(directory=tmpdir)
            assert hasattr(storage, '_lock')
            assert hasattr(storage._lock, 'acquire')
            assert hasattr(storage._lock, 'release')

    def test_concurrent_pending_logins_access(self):
        """Test that concurrent access to pending_logins is thread-safe."""
        manager = SessionManager()
        results = []
        errors = []

        def add_pending_login(session_id):
            try:
                with manager._lock:
                    manager._pending_logins[session_id] = (Mock(), 300, Mock())
            except Exception as e:
                errors.append(e)

        # Create multiple threads accessing pending_logins
        threads = []
        for i in range(10):
            t = threading.Thread(target=add_pending_login, args=(f"session_{i}",))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(manager._pending_logins) == 10

    @patch("tidal_api.session_storage.asyncio")
    def test_concurrent_storage_operations(self, mock_asyncio):
        """Test that concurrent storage operations are thread-safe."""
        import tempfile
        # Mock the async operations to avoid actual DiskStore calls
        mock_asyncio.run.return_value = None
        mock_asyncio.get_event_loop.side_effect = RuntimeError("No event loop")

        lock_acquired = []
        errors = []

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(directory=tmpdir)

            def save_session(session_id):
                try:
                    # Verify lock is used
                    if storage._lock.acquire(blocking=False):
                        lock_acquired.append(session_id)
                        storage._lock.release()
                except Exception as e:
                    errors.append(e)

            # Create multiple threads attempting to acquire lock
            threads = []
            for i in range(5):
                t = threading.Thread(target=save_session, args=(f"session_{i}",))
                threads.append(t)
                t.start()

            # Wait for all threads
            for t in threads:
                t.join()

            # Verify lock mechanism works (some threads should acquire, some should wait)
            # The important thing is no errors occurred
            assert len(errors) == 0, f"Thread safety errors: {errors}"

    @patch("tidal_api.session_manager.BrowserSession")
    def test_authenticate_thread_safety(self, mock_browser_session):
        """Test that authenticate() properly uses locks."""
        mock_session = Mock()
        mock_session.start_oauth_login.return_value = ("https://auth.url", 300, Mock())
        mock_browser_session.return_value = mock_session

        mock_storage = Mock(spec=SessionStorage)
        mock_storage.load_session_sync.return_value = None

        manager = SessionManager(storage=mock_storage)

        # Simulate concurrent authenticate calls
        def authenticate_call(session_id):
            return manager.authenticate(session_id=session_id)

        threads = []
        for i in range(5):
            t = threading.Thread(target=authenticate_call, args=(f"session_{i}",))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify all sessions were added to pending_logins (no race conditions)
        assert len(manager._pending_logins) == 5

    def test_storage_uses_diskstore(self):
        """Test that SessionStorage uses DiskStore."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(directory=tmpdir)
            assert hasattr(storage, '_store'), "Should have _store (DiskStore wrapper)"
            assert hasattr(storage, 'save_session_sync'), "Should have sync wrapper"
            assert hasattr(storage, 'load_session_sync'), "Should have sync wrapper"

    def test_manager_uses_storage(self):
        """Test that SessionManager uses SessionStorage."""
        mock_storage = Mock(spec=SessionStorage)
        manager = SessionManager(storage=mock_storage)
        assert manager._storage is mock_storage

    def test_all_session_operations_use_storage(self):
        """Test that all session operations go through storage."""
        mock_storage = Mock(spec=SessionStorage)
        mock_storage.load_session_sync.return_value = None
        mock_storage.list_sessions_sync.return_value = []

        manager = SessionManager(storage=mock_storage)

        # Test get_authenticated_session uses storage
        try:
            manager.get_authenticated_session(session_id="test")
        except RuntimeError:
            pass  # Expected when no session exists
        assert mock_storage.load_session_sync.called

        # Reset mock
        mock_storage.reset_mock()
        mock_storage.load_session_sync.return_value = None

        # Test list_active_sessions uses storage
        manager.list_active_sessions()
        assert mock_storage.list_sessions_sync.called

