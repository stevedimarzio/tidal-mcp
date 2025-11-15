"""
TIDAL API services (backward compatibility wrapper).

This module provides backward-compatible function-based API that wraps
the new TidalService class. New code should use TidalService directly.
"""

from typing import Any

try:
    from .session_manager import SessionManager
    from .tidal_service import TidalService
except ImportError:
    from session_manager import SessionManager
    from tidal_service import TidalService

# Global service instance for backward compatibility
_service = TidalService(SessionManager())


def get_favorite_tracks(limit: int = 20) -> dict[str, Any]:
    """Get tracks from user's favorites (backward compatibility)."""
    response = _service.get_favorite_tracks(limit=limit)
    return {"tracks": [track.model_dump() for track in response.tracks]}


def get_track_recommendations(track_id: str, limit: int = 20) -> dict[str, Any]:
    """Get recommended tracks based on a specific track (backward compatibility)."""
    response = _service.get_track_recommendations(track_id=track_id, limit=limit)
    return {"recommendations": [track.model_dump() for track in response.recommendations]}


def get_batch_recommendations(
    track_ids: list[str], limit_per_track: int = 20, remove_duplicates: bool = True
) -> dict[str, Any]:
    """Get recommended tracks based on multiple track IDs (backward compatibility)."""
    response = _service.get_batch_recommendations(
        track_ids=track_ids, limit_per_track=limit_per_track, remove_duplicates=remove_duplicates
    )
    return {"recommendations": [track.model_dump() for track in response.recommendations]}


def create_playlist(title: str, track_ids: list[str], description: str = "") -> dict[str, Any]:
    """Create a new TIDAL playlist with specified tracks (backward compatibility)."""
    response = _service.create_playlist(title=title, track_ids=track_ids, description=description)
    return {
        "status": response.status,
        "message": response.message,
        "playlist": response.playlist.model_dump(),
    }


def get_user_playlists() -> dict[str, Any]:
    """Get user's playlists from TIDAL (backward compatibility)."""
    response = _service.get_user_playlists()
    return {"playlists": [playlist.model_dump() for playlist in response.playlists]}


def get_playlist_tracks(playlist_id: str, limit: int = 100) -> dict[str, Any]:
    """Get tracks from a specific TIDAL playlist (backward compatibility)."""
    response = _service.get_playlist_tracks(playlist_id=playlist_id, limit=limit)
    return {
        "playlist_id": response.playlist_id,
        "tracks": [track.model_dump() for track in response.tracks],
        "total_tracks": response.total_tracks,
    }


def delete_playlist(playlist_id: str) -> dict[str, Any]:
    """Delete a TIDAL playlist by its ID (backward compatibility)."""
    response = _service.delete_playlist(playlist_id=playlist_id)
    return {"status": response.status, "message": response.message}


def search_tidal(
    query: str, limit: int = 20, search_types: str = "tracks,albums,artists"
) -> dict[str, Any]:
    """Search for tracks, albums, and/or artists on TIDAL (backward compatibility)."""
    response = _service.search_tidal(query=query, limit=limit, search_types=search_types)
    return {
        "query": response.query,
        "results": {
            "tracks": [track.model_dump() for track in response.results.tracks],
            "albums": [album.model_dump() for album in response.results.albums],
            "artists": [artist.model_dump() for artist in response.results.artists],
        },
        "total_tracks": response.total_tracks,
        "total_albums": response.total_albums,
        "total_artists": response.total_artists,
    }


def search_tracks(query: str, limit: int = 20) -> dict[str, Any]:
    """Search for tracks on TIDAL (backward compatibility)."""
    response = _service.search_tracks(query=query, limit=limit)
    return {
        "query": response.query,
        "tracks": [track.model_dump() for track in response.tracks],
        "total": response.total,
    }


def search_albums(query: str, limit: int = 20) -> dict[str, Any]:
    """Search for albums on TIDAL (backward compatibility)."""
    response = _service.search_albums(query=query, limit=limit)
    return {
        "query": response.query,
        "albums": [album.model_dump() for album in response.albums],
        "total": response.total,
    }


def search_artists(query: str, limit: int = 20) -> dict[str, Any]:
    """Search for artists on TIDAL (backward compatibility)."""
    response = _service.search_artists(query=query, limit=limit)
    return {
        "query": response.query,
        "artists": [artist.model_dump() for artist in response.artists],
        "total": response.total,
    }
