def format_track_data(track, source_track_id=None):
    """
    Format a track object into a standardized dictionary.
    
    Args:
        track: TIDAL track object
        source_track_id: Optional ID of the track that led to this recommendation
        
    Returns:
        Dictionary with standardized track information
    """
    # Safely get artist name
    artist_name = "Unknown"
    try:
        if hasattr(track, 'artist') and track.artist:
            if hasattr(track.artist, 'name'):
                artist_name = track.artist.name
            elif isinstance(track.artist, str):
                artist_name = track.artist
            elif hasattr(track.artist, '__str__'):
                artist_name = str(track.artist)
    except (AttributeError, TypeError):
        pass
    
    # Safely get album name
    album_name = "Unknown"
    try:
        if hasattr(track, 'album') and track.album:
            if hasattr(track.album, 'name'):
                album_name = track.album.name
            elif isinstance(track.album, str):
                album_name = track.album
            elif hasattr(track.album, '__str__'):
                album_name = str(track.album)
    except (AttributeError, TypeError):
        pass
    
    # Safely get track ID and name
    track_id = getattr(track, 'id', None)
    track_name = getattr(track, 'name', 'Unknown Track')
    duration = getattr(track, 'duration', 0)
    
    track_data = {
        "id": track_id,
        "title": track_name,
        "artist": artist_name,
        "album": album_name,
        "duration": duration,
        "url": f"https://tidal.com/browse/track/{track_id}?u" if track_id else None
    }
    
    # Include source track ID if provided
    if source_track_id:
        track_data["source_track_id"] = source_track_id
        
    return track_data

def bound_limit(limit: int, max_n: int = 50) -> int:
    # Ensure limit is within reasonable bounds
    if limit < 1:
        limit = 1
    elif limit > max_n:
        limit = max_n
    print(f"Limit set to {limit} (max {max_n})")    
    return limit
