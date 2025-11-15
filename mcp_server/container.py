"""Dependency injection container."""

try:
    from tidal_api.session_manager import SessionManager
    from tidal_api.tidal_service import TidalService
except ImportError:
    import sys
    from pathlib import Path

    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from tidal_api.session_manager import SessionManager
    from tidal_api.tidal_service import TidalService


class Container:
    """Simple dependency injection container."""

    def __init__(self):
        self._session_manager: SessionManager | None = None
        self._tidal_service: TidalService | None = None

    @property
    def session_manager(self) -> SessionManager:
        """Get session manager instance (singleton)."""
        if self._session_manager is None:
            self._session_manager = SessionManager()
        return self._session_manager

    @property
    def tidal_service(self) -> TidalService:
        """Get TIDAL service instance (singleton)."""
        if self._tidal_service is None:
            self._tidal_service = TidalService(self.session_manager)
        return self._tidal_service


# Global container instance
container = Container()
