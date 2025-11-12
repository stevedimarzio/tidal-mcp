# Handle imports for both module and direct execution
try:
    from .models import TrackModel, AlbumModel, ArtistModel, RecentlyPlayedItem, PlaybackHistoryItem, ArtistPlaybackStats
except ImportError:
    from models import TrackModel, AlbumModel, ArtistModel, RecentlyPlayedItem, PlaybackHistoryItem, ArtistPlaybackStats


def _safe_get_attr(obj, attr: str, default=None):
    """Safely get an attribute from an object."""
    try:
        return getattr(obj, attr, default)
    except (AttributeError, TypeError):
        return default


def _safe_get_name(obj) -> str:
    """Safely extract a name from an object (artist, album, etc.)."""
    if obj is None:
        return "Unknown"
    
    try:
        if hasattr(obj, 'name'):
            return obj.name
        elif isinstance(obj, str):
            return obj
        elif hasattr(obj, '__str__'):
            return str(obj)
    except (AttributeError, TypeError):
        pass
    
    return "Unknown"


def format_track_data(track, source_track_id: str = None) -> TrackModel:
    """
    Format a track object into a TrackModel.
    
    Args:
        track: TIDAL track object
        source_track_id: Optional ID of the track that led to this recommendation
        
    Returns:
        TrackModel with standardized track information
    """
    track_id = _safe_get_attr(track, 'id')
    track_name = _safe_get_attr(track, 'name', 'Unknown Track')
    duration = _safe_get_attr(track, 'duration', 0)
    artist_obj = _safe_get_attr(track, 'artist')
    album_obj = _safe_get_attr(track, 'album')
    
    artist_name = _safe_get_name(artist_obj)
    album_name = _safe_get_name(album_obj)
    
    url = f"https://tidal.com/browse/track/{track_id}?u" if track_id else None
    
    return TrackModel(
        id=str(track_id) if track_id else None,
        title=track_name,
        artist=artist_name,
        album=album_name,
        duration=duration or 0,
        url=url,
        source_track_id=str(source_track_id) if source_track_id else None
    )

def format_album_data(album) -> AlbumModel:
    """
    Format an album object into an AlbumModel.
    
    Args:
        album: TIDAL album object
        
    Returns:
        AlbumModel with standardized album information
    """
    album_id = _safe_get_attr(album, 'id')
    album_name = _safe_get_attr(album, 'name', 'Unknown Album')
    release_date = _safe_get_attr(album, 'release_date')
    duration = _safe_get_attr(album, 'duration', 0)
    num_tracks = _safe_get_attr(album, 'num_tracks', 0)
    artist_obj = _safe_get_attr(album, 'artist')
    
    artist_name = _safe_get_name(artist_obj)
    url = f"https://tidal.com/browse/album/{album_id}?u" if album_id else None
    
    return AlbumModel(
        id=str(album_id) if album_id else None,
        title=album_name,
        artist=artist_name,
        release_date=str(release_date) if release_date else None,
        duration=duration or 0,
        num_tracks=num_tracks or 0,
        url=url
    )

def format_artist_data(artist) -> ArtistModel:
    """
    Format an artist object into an ArtistModel.
    
    Args:
        artist: TIDAL artist object
        
    Returns:
        ArtistModel with standardized artist information
    """
    artist_id = _safe_get_attr(artist, 'id')
    artist_name = _safe_get_attr(artist, 'name', 'Unknown Artist')
    url = f"https://tidal.com/browse/artist/{artist_id}?u" if artist_id else None
    
    return ArtistModel(
        id=str(artist_id) if artist_id else None,
        name=artist_name,
        url=url
    )

def format_recently_played_item(track, played_at=None) -> RecentlyPlayedItem:
    """
    Format a track object into a RecentlyPlayedItem with timestamp.
    
    Args:
        track: TIDAL track object or dict with track information
        played_at: Optional datetime when the track was played
        
    Returns:
        RecentlyPlayedItem with standardized track information and timestamp
    """
    # Handle both track objects and dicts
    if isinstance(track, dict):
        track_id = track.get('id')
        track_name = track.get('name', track.get('title', 'Unknown Track'))
        duration = track.get('duration', 0)
        artist_obj = track.get('artist')
        album_obj = track.get('album')
        played_at = track.get('played_at') or played_at
    else:
        track_id = _safe_get_attr(track, 'id')
        track_name = _safe_get_attr(track, 'name', 'Unknown Track')
        duration = _safe_get_attr(track, 'duration', 0)
        artist_obj = _safe_get_attr(track, 'artist')
        album_obj = _safe_get_attr(track, 'album')
        # Try to get played_at from track object if available
        if played_at is None:
            played_at = _safe_get_attr(track, 'played_at')
    
    artist_name = _safe_get_name(artist_obj)
    album_name = _safe_get_name(album_obj)
    
    url = f"https://tidal.com/browse/track/{track_id}?u" if track_id else None
    
    return RecentlyPlayedItem(
        id=str(track_id) if track_id else None,
        title=track_name,
        artist=artist_name,
        album=album_name,
        duration=duration or 0,
        url=url,
        played_at=played_at
    )


def format_playback_history_item(track, play_count: int = 1, first_played=None, last_played=None) -> PlaybackHistoryItem:
    """
    Format a track object into a PlaybackHistoryItem with play count and timestamps.
    
    Args:
        track: TIDAL track object or dict with track information
        play_count: Number of times the track was played
        first_played: Optional datetime when the track was first played
        last_played: Optional datetime when the track was last played
        
    Returns:
        PlaybackHistoryItem with standardized track information, play count, and timestamps
    """
    # Handle both track objects and dicts
    if isinstance(track, dict):
        track_id = track.get('id')
        track_name = track.get('name', track.get('title', 'Unknown Track'))
        duration = track.get('duration', 0)
        artist_obj = track.get('artist')
        album_obj = track.get('album')
        play_count = track.get('play_count', play_count)
        first_played = track.get('first_played') or first_played
        last_played = track.get('last_played') or last_played
    else:
        track_id = _safe_get_attr(track, 'id')
        track_name = _safe_get_attr(track, 'name', 'Unknown Track')
        duration = _safe_get_attr(track, 'duration', 0)
        artist_obj = _safe_get_attr(track, 'artist')
        album_obj = _safe_get_attr(track, 'album')
        # Try to get play count and timestamps from track object if available
        if play_count == 1:
            play_count = _safe_get_attr(track, 'play_count', 1)
        if first_played is None:
            first_played = _safe_get_attr(track, 'first_played')
        if last_played is None:
            last_played = _safe_get_attr(track, 'last_played')
    
    artist_name = _safe_get_name(artist_obj)
    album_name = _safe_get_name(album_obj)
    
    url = f"https://tidal.com/browse/track/{track_id}?u" if track_id else None
    
    return PlaybackHistoryItem(
        id=str(track_id) if track_id else None,
        title=track_name,
        artist=artist_name,
        album=album_name,
        duration=duration or 0,
        url=url,
        play_count=play_count,
        first_played=first_played,
        last_played=last_played
    )


def bound_limit(limit: int, max_n: int = 50) -> int:
    # Ensure limit is within reasonable bounds
    if limit < 1:
        limit = 1
    elif limit > max_n:
        limit = max_n
    # Note: Logging removed here to avoid noise - limit validation is sufficient
    return limit
