"""Dependency injection configuration using IoC pattern."""

from tidal_api.session_manager import SessionManager
from tidal_api.tidal_service import TidalService

# Lazy initialization of services (singleton pattern)
_session_manager: SessionManager | None = None
_tidal_service: TidalService | None = None


class Container:
    """Dependency injection container using IoC pattern."""

    @property
    def session_manager(self) -> SessionManager:
        """Get SessionManager instance (singleton)."""
        global _session_manager
        if _session_manager is None:
            _session_manager = SessionManager()
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

