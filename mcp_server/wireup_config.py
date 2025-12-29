"""Dependency injection configuration using IoC pattern."""

import os
from pathlib import Path

from tidal_api.session_manager import SessionManager
from tidal_api.session_storage import SessionStorage
from tidal_api.tidal_service import TidalService

# Lazy initialization of services (singleton pattern)
_session_storage: SessionStorage | None = None
_session_manager: SessionManager | None = None
_tidal_service: TidalService | None = None


class Container:
    """Dependency injection container using IoC pattern."""

    @property
    def session_storage(self) -> SessionStorage:
        """Get SessionStorage instance (singleton)."""
        global _session_storage
        if _session_storage is None:
            # Use home directory for storage
            home_dir = os.path.expanduser("~")
            directory = os.path.join(home_dir, ".tidal-mcp", "sessions")
            os.makedirs(directory, exist_ok=True, mode=0o700)

            # Get encryption key from environment
            encryption_key = os.getenv("TIDAL_STORAGE_ENCRYPTION_KEY")

            _session_storage = SessionStorage(directory=directory, encryption_key=encryption_key)
        return _session_storage

    @property
    def session_manager(self) -> SessionManager:
        """Get SessionManager instance (singleton)."""
        global _session_manager
        if _session_manager is None:
            _session_manager = SessionManager(storage=self.session_storage)
        return _session_manager

    @property
    def tidal_service(self) -> TidalService:
        """Get TidalService instance (singleton)."""
        global _tidal_service
        if _tidal_service is None:
            _tidal_service = TidalService(self.session_manager)
        return _tidal_service


# Global container instance
container = Container()

