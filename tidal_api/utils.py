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

def format_album_data(album):
    """
    Format an album object into a standardized dictionary.
    
    Args:
        album: TIDAL album object
        
    Returns:
        Dictionary with standardized album information
    """
    # Safely get artist name
    artist_name = "Unknown"
    try:
        if hasattr(album, 'artist') and album.artist:
            if hasattr(album.artist, 'name'):
                artist_name = album.artist.name
            elif isinstance(album.artist, str):
                artist_name = album.artist
            elif hasattr(album.artist, '__str__'):
                artist_name = str(album.artist)
    except (AttributeError, TypeError):
        pass
    
    album_id = getattr(album, 'id', None)
    album_name = getattr(album, 'name', 'Unknown Album')
    release_date = getattr(album, 'release_date', None)
    duration = getattr(album, 'duration', 0)
    num_tracks = getattr(album, 'num_tracks', 0)
    
    album_data = {
        "id": album_id,
        "title": album_name,
        "artist": artist_name,
        "release_date": release_date,
        "duration": duration,
        "num_tracks": num_tracks,
        "url": f"https://tidal.com/browse/album/{album_id}?u" if album_id else None
    }
    
    return album_data

def format_artist_data(artist):
    """
    Format an artist object into a standardized dictionary.
    
    Args:
        artist: TIDAL artist object
        
    Returns:
        Dictionary with standardized artist information
    """
    artist_id = getattr(artist, 'id', None)
    artist_name = getattr(artist, 'name', 'Unknown Artist')
    
    artist_data = {
        "id": artist_id,
        "name": artist_name,
        "url": f"https://tidal.com/browse/artist/{artist_id}?u" if artist_id else None
    }
    
    return artist_data

def bound_limit(limit: int, max_n: int = 50) -> int:
    # Ensure limit is within reasonable bounds
    if limit < 1:
        limit = 1
    elif limit > max_n:
        limit = max_n
    print(f"Limit set to {limit} (max {max_n})")    
    return limit
