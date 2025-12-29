"""Unit tests for session storage."""

import tempfile
from pathlib import Path

import pytest

try:
    from tidal_api.session_storage import SessionStorage
except ImportError:
    import sys
    from pathlib import Path as PathLib

    sys.path.insert(0, str(PathLib(__file__).parent.parent.parent))
    from tidal_api.session_storage import SessionStorage


@pytest.mark.unit
class TestSessionStorage:
    """Test SessionStorage class."""

    def test_save_and_load_session(self):
        """Test saving and loading a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(directory=tmpdir)
            session_id = "test_session_1"
            session_data = {
                "token_type": "Bearer",
                "access_token": "test_access_token",
                "refresh_token": "test_refresh_token",
                "session_id": session_id,
                "is_pkce": False,
            }

            # Save session
            storage.save_session_sync(session_id, session_data)

            # Load session
            loaded_data = storage.load_session_sync(session_id)

            assert loaded_data is not None
            assert loaded_data == session_data
            assert loaded_data["session_id"] == session_id

    def test_list_sessions(self):
        """Test listing all sessions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(directory=tmpdir)

            # Initially empty
            sessions = storage.list_sessions_sync()
            assert len(sessions) == 0

            # Add sessions
            session_data_1 = {
                "token_type": "Bearer",
                "access_token": "token1",
                "refresh_token": "refresh1",
                "session_id": "session1",
                "is_pkce": False,
            }
            session_data_2 = {
                "token_type": "Bearer",
                "access_token": "token2",
                "refresh_token": "refresh2",
                "session_id": "session2",
                "is_pkce": False,
            }

            storage.save_session_sync("session1", session_data_1)
            storage.save_session_sync("session2", session_data_2)

            # List sessions
            sessions = storage.list_sessions_sync()
            assert len(sessions) == 2
            assert "session1" in sessions
            assert "session2" in sessions

    def test_delete_session(self):
        """Test deleting a session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(directory=tmpdir)
            session_id = "test_session_delete"
            session_data = {
                "token_type": "Bearer",
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "session_id": session_id,
                "is_pkce": False,
            }

            # Save session
            storage.save_session_sync(session_id, session_data)

            # Verify it exists
            assert storage.session_exists_sync(session_id) is True
            assert session_id in storage.list_sessions_sync()

            # Delete session
            storage.delete_session_sync(session_id)

            # Verify it's gone
            assert storage.session_exists_sync(session_id) is False
            assert session_id not in storage.list_sessions_sync()
            assert storage.load_session_sync(session_id) is None

    def test_session_exists(self):
        """Test checking if session exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(directory=tmpdir)
            session_id = "test_session_exists"
            session_data = {
                "token_type": "Bearer",
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "session_id": session_id,
                "is_pkce": False,
            }

            # Initially doesn't exist
            assert storage.session_exists_sync(session_id) is False

            # Save session
            storage.save_session_sync(session_id, session_data)

            # Now exists
            assert storage.session_exists_sync(session_id) is True

    def test_index_persistence(self):
        """Test that index persists across storage instances."""
        from cryptography.fernet import Fernet

        with tempfile.TemporaryDirectory() as tmpdir:
            # Generate a consistent encryption key for both instances
            key = Fernet.generate_key()
            encryption_key = key.decode("utf-8")  # Fernet key is already base64-encoded

            # Create first storage instance and save sessions
            storage1 = SessionStorage(directory=tmpdir, encryption_key=encryption_key)
            storage1.save_session_sync("session1", {"session_id": "session1", "token": "token1"})
            storage1.save_session_sync("session2", {"session_id": "session2", "token": "token2"})

            # Create second storage instance (simulating restart) with same key
            storage2 = SessionStorage(directory=tmpdir, encryption_key=encryption_key)

            # Verify sessions are still listed
            sessions = storage2.list_sessions_sync()
            assert len(sessions) == 2
            assert "session1" in sessions
            assert "session2" in sessions

            # Verify sessions can be loaded
            assert storage2.load_session_sync("session1") is not None
            assert storage2.load_session_sync("session2") is not None

    def test_no_file_index_created(self):
        """Test that no .sessions_index.json file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(directory=tmpdir)
            session_id = "test_session"
            session_data = {
                "token_type": "Bearer",
                "access_token": "test_token",
                "refresh_token": "test_refresh",
                "session_id": session_id,
                "is_pkce": False,
            }

            # Save session
            storage.save_session_sync(session_id, session_data)

            # Verify no .sessions_index.json file exists
            index_file = Path(tmpdir) / ".sessions_index.json"
            assert not index_file.exists(), "File-based index should not be created"

            # But sessions should still be listable
            sessions = storage.list_sessions_sync()
            assert session_id in sessions

