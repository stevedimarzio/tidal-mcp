"""
DiskStore-based session storage with encryption and thread safety.

Provides persistent, encrypted storage for TIDAL OAuth sessions using FastMCP's
DiskStore infrastructure.
"""

import asyncio
import json
import os
import threading

from cryptography.fernet import Fernet

try:
    from .logger import logger
except ImportError:
    from logger import logger

try:
    from key_value.aio.stores.disk import DiskStore
    from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
except ImportError:
    # Fallback if not available
    DiskStore = None
    FernetEncryptionWrapper = None


class SessionStorage:
    """DiskStore-based session storage with encryption and thread safety."""

    INDEX_KEY = "__sessions_index__"

    def __init__(self, directory: str, encryption_key: str | None = None):
        """
        Initialize session storage.

        Args:
            directory: Directory for DiskStore (defaults to ~/.tidal-mcp/sessions)
            encryption_key: Optional Fernet encryption key (base64 encoded string)
                          If None, generates new key or loads from env
        """
        if DiskStore is None or FernetEncryptionWrapper is None:
            raise ImportError(
                "key_value.aio is required. Install with: pip install 'py-key-value-aio'"
            )

        self._directory = directory
        self._lock = threading.Lock()  # Thread safety for async operations

        # Initialize encryption
        if encryption_key:
            fernet = Fernet(encryption_key.encode())
        else:
            # Try environment variable
            env_key = os.getenv("TIDAL_STORAGE_ENCRYPTION_KEY")
            if env_key:
                fernet = Fernet(env_key.encode())
            else:
                # Generate new key (log warning for production)
                key = Fernet.generate_key()
                fernet = Fernet(key)
                logger.warning(
                    "Generated new encryption key. Set TIDAL_STORAGE_ENCRYPTION_KEY "
                    "for production deployments."
                )

        # Initialize DiskStore with encryption wrapper
        disk_store = DiskStore(directory=str(self._directory))
        self._store = FernetEncryptionWrapper(key_value=disk_store, fernet=fernet)

    def _run_async(self, coro):
        """Thread-safe wrapper for async operations."""
        with self._lock:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is running, use thread pool
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, coro)
                        return future.result()
                else:
                    return loop.run_until_complete(coro)
            except RuntimeError:
                return asyncio.run(coro)

    async def _load_index(self) -> set[str]:
        """Load session index from DiskStore."""
        try:
            index_data = await self._store.get(self.INDEX_KEY)
            if index_data is None:
                return set()
            if isinstance(index_data, bytes):
                # Handle legacy format (bytes)
                index_data = json.loads(index_data.decode("utf-8"))
            return set(index_data.get("session_ids", []))
        except Exception as e:
            logger.debug(f"Could not load session index: {e}")
            return set()

    async def _save_index(self, session_ids: set[str]) -> None:
        """Save session index to DiskStore."""
        try:
            index_data = {"session_ids": list(session_ids)}
            await self._store.put(self.INDEX_KEY, index_data)
        except Exception as e:
            logger.debug(f"Could not save session index: {e}")

    async def save_session(self, session_id: str, session_data: dict) -> None:
        """Save session data to DiskStore and update index."""
        key = f"session:{session_id}"
        await self._store.put(key, session_data)

        # Update index in DiskStore
        session_ids = await self._load_index()
        session_ids.add(session_id)
        await self._save_index(session_ids)

    async def load_session(self, session_id: str) -> dict | None:
        """Load session data from DiskStore."""
        key = f"session:{session_id}"
        try:
            value = await self._store.get(key)
            if value is None:
                return None
            if isinstance(value, bytes):
                # Handle legacy format (bytes)
                return json.loads(value.decode("utf-8"))
            return value
        except Exception as e:
            logger.debug(f"Could not load session {session_id}: {e}")
            return None

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        data = await self.load_session(session_id)
        return data is not None

    async def list_sessions(self) -> list[str]:
        """
        List all session IDs.

        Returns session IDs from the index stored in DiskStore.
        """
        session_ids = await self._load_index()
        return list(session_ids)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and update index."""
        key = f"session:{session_id}"
        await self._store.delete(key)

        # Update index in DiskStore
        session_ids = await self._load_index()
        session_ids.discard(session_id)
        await self._save_index(session_ids)

    # Sync wrappers for SessionManager
    def save_session_sync(self, session_id: str, session_data: dict) -> None:
        """Thread-safe sync wrapper for save_session."""
        return self._run_async(self.save_session(session_id, session_data))

    def load_session_sync(self, session_id: str) -> dict | None:
        """Thread-safe sync wrapper for load_session."""
        return self._run_async(self.load_session(session_id))

    def session_exists_sync(self, session_id: str) -> bool:
        """Thread-safe sync wrapper for session_exists."""
        return self._run_async(self.session_exists(session_id))

    def list_sessions_sync(self) -> list[str]:
        """Thread-safe sync wrapper for list_sessions."""
        return self._run_async(self.list_sessions())

    def delete_session_sync(self, session_id: str) -> None:
        """Thread-safe sync wrapper for delete_session."""
        return self._run_async(self.delete_session(session_id))

