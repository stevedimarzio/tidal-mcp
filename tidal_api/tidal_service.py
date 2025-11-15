"""
TIDAL service with dependency injection.

Core business logic for TIDAL operations using dependency injection.
"""

import concurrent.futures

try:
    from .interfaces import ISessionManager
    from .logger import logger
    from .models import (
        BatchRecommendationsResponse,
        CreatePlaylistResponse,
        DeletePlaylistResponse,
        PlaylistModel,
        PlaylistsResponse,
        PlaylistTracksResponse,
        RecommendationsResponse,
        SearchAlbumsResponse,
        SearchArtistsResponse,
        SearchResponse,
        SearchResultsModel,
        SearchTracksResponse,
        TrackModel,
        TracksResponse,
    )
    from .utils import (
        TIDAL_PLAYLIST_URL_TEMPLATE,
        bound_limit,
        format_album_data,
        format_artist_data,
        format_track_data,
    )
except ImportError:
    from interfaces import ISessionManager
    from logger import logger
    from models import (
        BatchRecommendationsResponse,
        CreatePlaylistResponse,
        DeletePlaylistResponse,
        PlaylistModel,
        PlaylistsResponse,
        PlaylistTracksResponse,
        RecommendationsResponse,
        SearchAlbumsResponse,
        SearchArtistsResponse,
        SearchResponse,
        SearchResultsModel,
        SearchTracksResponse,
        TrackModel,
        TracksResponse,
    )
    from utils import (
        TIDAL_PLAYLIST_URL_TEMPLATE,
        bound_limit,
        format_album_data,
        format_artist_data,
        format_track_data,
    )


class TidalService:
    """Service for TIDAL operations with dependency injection."""

    def __init__(self, session_manager: ISessionManager):
        """
        Initialize TIDAL service.

        Args:
            session_manager: Session manager for authentication
        """
        self.session_manager = session_manager

    def get_favorite_tracks(self, limit: int = 20) -> TracksResponse:
        """Get tracks from user's favorites."""
        session = self.session_manager.get_authenticated_session()
        favorites = session.user.favorites
        limit = bound_limit(limit)

        try:
            tracks = favorites.tracks(limit=limit, order="DATE", order_direction="DESC")
            if hasattr(tracks, "__iter__") and not isinstance(tracks, (list, tuple, str)):
                tracks = list(tracks)
        except Exception:
            tracks = favorites.tracks(limit=limit)
            if hasattr(tracks, "__iter__") and not isinstance(tracks, (list, tuple, str)):
                tracks = list(tracks)

        track_list = []
        for track in tracks:
            try:
                track_list.append(format_track_data(track))
            except Exception as e:
                logger.warning(f"Error formatting track: {e}")
                continue

        return TracksResponse(tracks=track_list)

    def get_track_recommendations(self, track_id: str, limit: int = 20) -> RecommendationsResponse:
        """Get recommended tracks based on a specific track."""
        session = self.session_manager.get_authenticated_session()
        limit = bound_limit(limit)

        track = session.track(track_id)
        if not track:
            raise ValueError(f"Track with ID {track_id} not found")

        recommendations = track.get_track_radio(limit=limit)
        track_list = [format_track_data(track) for track in recommendations]

        return RecommendationsResponse(recommendations=track_list)

    def get_batch_recommendations(
        self, track_ids: list[str], limit_per_track: int = 20, remove_duplicates: bool = True
    ) -> BatchRecommendationsResponse:
        """Get recommended tracks based on multiple track IDs."""
        session = self.session_manager.get_authenticated_session()
        limit_per_track = bound_limit(limit_per_track)

        def get_track_recommendations_single(track_id: str) -> list[TrackModel]:
            try:
                track = session.track(track_id)
                recommendations = track.get_track_radio(limit=limit_per_track)
                return [format_track_data(rec, source_track_id=track_id) for rec in recommendations]
            except Exception as e:
                logger.warning(f"Error getting recommendations for track {track_id}: {str(e)}")
                return []

        all_recommendations = []
        seen_track_ids = set()

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(track_ids)) as executor:
            future_to_track_id = {
                executor.submit(get_track_recommendations_single, track_id): track_id
                for track_id in track_ids
            }

            for future in concurrent.futures.as_completed(future_to_track_id):
                track_recommendations = future.result()

                for track_data in track_recommendations:
                    track_id = track_data.id

                    if remove_duplicates and track_id and track_id in seen_track_ids:
                        continue

                    all_recommendations.append(track_data)
                    if track_id:
                        seen_track_ids.add(track_id)

        return BatchRecommendationsResponse(recommendations=all_recommendations)

    def create_playlist(
        self, title: str, track_ids: list[str], description: str = ""
    ) -> CreatePlaylistResponse:
        """Create a new TIDAL playlist with specified tracks."""
        session = self.session_manager.get_authenticated_session()

        playlist = session.user.create_playlist(title, description)
        playlist.add(track_ids)

        playlist_info = PlaylistModel(
            id=str(playlist.id),
            title=playlist.name,
            description=getattr(playlist, "description", "") or "",
            created=getattr(playlist, "created", None),
            last_updated=getattr(playlist, "last_updated", None),
            track_count=getattr(playlist, "num_tracks", 0) or 0,
            duration=getattr(playlist, "duration", 0) or 0,
            url=TIDAL_PLAYLIST_URL_TEMPLATE.format(playlist_id=playlist.id),
        )

        return CreatePlaylistResponse(
            status="success",
            message=f"Successfully created playlist '{title}' with {len(track_ids)} tracks",
            playlist=playlist_info,
        )

    def get_user_playlists(self) -> PlaylistsResponse:
        """Get user's playlists from TIDAL."""
        session = self.session_manager.get_authenticated_session()
        playlists = session.user.playlists()

        playlist_list = []
        for playlist in playlists:
            playlist_info = PlaylistModel(
                id=str(playlist.id),
                title=playlist.name,
                description=getattr(playlist, "description", "") or "",
                created=getattr(playlist, "created", None),
                last_updated=getattr(playlist, "last_updated", None),
                track_count=getattr(playlist, "num_tracks", 0) or 0,
                duration=getattr(playlist, "duration", 0) or 0,
                url=TIDAL_PLAYLIST_URL_TEMPLATE.format(playlist_id=playlist.id),
            )
            playlist_list.append(playlist_info)

        sorted_playlists = sorted(playlist_list, key=lambda x: x.last_updated or "", reverse=True)

        return PlaylistsResponse(playlists=sorted_playlists)

    def get_playlist_tracks(self, playlist_id: str, limit: int = 100) -> PlaylistTracksResponse:
        """Get tracks from a specific TIDAL playlist."""
        session = self.session_manager.get_authenticated_session()
        limit = bound_limit(limit, max_n=100)

        playlist = session.playlist(playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with ID {playlist_id} not found")

        tracks = playlist.items(limit=limit)
        track_list = [format_track_data(track) for track in tracks]

        return PlaylistTracksResponse(
            playlist_id=str(playlist.id), tracks=track_list, total_tracks=len(track_list)
        )

    def delete_playlist(self, playlist_id: str) -> DeletePlaylistResponse:
        """Delete a TIDAL playlist by its ID."""
        session = self.session_manager.get_authenticated_session()

        playlist = session.playlist(playlist_id)
        if not playlist:
            raise ValueError(f"Playlist with ID {playlist_id} not found")

        playlist.delete()

        return DeletePlaylistResponse(
            status="success", message=f"Playlist with ID {playlist_id} was successfully deleted"
        )

    def search_tidal(
        self, query: str, limit: int = 20, search_types: str = "tracks,albums,artists"
    ) -> SearchResponse:
        """Search for tracks, albums, and/or artists on TIDAL."""
        import tidalapi

        session = self.session_manager.get_authenticated_session()
        limit = bound_limit(limit)
        types_list = [t.strip().lower() for t in search_types.split(",")]

        models = []
        if "tracks" in types_list:
            models.append(tidalapi.Track)
        if "albums" in types_list:
            models.append(tidalapi.Album)
        if "artists" in types_list:
            models.append(tidalapi.Artist)

        if not models:
            raise ValueError("Invalid types. Must include at least one of: tracks, albums, artists")

        results = session.search(query, models=models, limit=limit)

        formatted_results = SearchResultsModel(tracks=[], albums=[], artists=[])

        if "tracks" in types_list and "tracks" in results:
            formatted_results.tracks = [format_track_data(track) for track in results["tracks"]]

        if "albums" in types_list and "albums" in results:
            formatted_results.albums = [format_album_data(album) for album in results["albums"]]

        if "artists" in types_list and "artists" in results:
            formatted_results.artists = [
                format_artist_data(artist) for artist in results["artists"]
            ]

        return SearchResponse(
            query=query,
            results=formatted_results,
            total_tracks=len(formatted_results.tracks),
            total_albums=len(formatted_results.albums),
            total_artists=len(formatted_results.artists),
        )

    def search_tracks(self, query: str, limit: int = 20) -> SearchTracksResponse:
        """Search for tracks on TIDAL."""
        import tidalapi

        session = self.session_manager.get_authenticated_session()
        limit = bound_limit(limit)
        results = session.search(query, models=[tidalapi.Track], limit=limit)

        tracks = results.get("tracks", [])
        formatted_tracks = [format_track_data(track) for track in tracks]

        return SearchTracksResponse(
            query=query, tracks=formatted_tracks, total=len(formatted_tracks)
        )

    def search_albums(self, query: str, limit: int = 20) -> SearchAlbumsResponse:
        """Search for albums on TIDAL."""
        import tidalapi

        session = self.session_manager.get_authenticated_session()
        limit = bound_limit(limit)
        results = session.search(query, models=[tidalapi.Album], limit=limit)

        albums = results.get("albums", [])
        formatted_albums = [format_album_data(album) for album in albums]

        return SearchAlbumsResponse(
            query=query, albums=formatted_albums, total=len(formatted_albums)
        )

    def search_artists(self, query: str, limit: int = 20) -> SearchArtistsResponse:
        """Search for artists on TIDAL."""
        import tidalapi

        session = self.session_manager.get_authenticated_session()
        limit = bound_limit(limit)
        results = session.search(query, models=[tidalapi.Artist], limit=limit)

        artists = results.get("artists", [])
        formatted_artists = [format_artist_data(artist) for artist in artists]

        return SearchArtistsResponse(
            query=query, artists=formatted_artists, total=len(formatted_artists)
        )
