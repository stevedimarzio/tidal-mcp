"""
TIDAL MCP FastAPI Application.

This module provides the REST API endpoints for TIDAL MCP functionality.
All endpoints use Pydantic models for request/response validation.
"""
import os
import tempfile
import concurrent.futures
from typing import List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import ssl
import sys

from fastapi import FastAPI, HTTPException, Depends, Query

# Handle imports for both module and direct execution
try:
    from .logger import logger
    from .browser_session import BrowserSession
    from .utils import format_track_data, format_album_data, format_artist_data, bound_limit, format_recently_played_item, format_playback_history_item, _safe_get_attr
    from .models import (
        LoginResponse,
        AuthStatusResponse,
        UserModel,
        TracksResponse,
        RecommendationsResponse,
        BatchRecommendationsRequest,
        BatchRecommendationsResponse,
        CreatePlaylistRequest,
        CreatePlaylistResponse,
        PlaylistModel,
        PlaylistsResponse,
        PlaylistTracksResponse,
        DeletePlaylistResponse,
        SearchResponse,
        SearchResultsModel,
        SearchTracksResponse,
        SearchAlbumsResponse,
        SearchArtistsResponse,
        RecentlyPlayedResponse,
        RecentlyPlayedItem,
        PlaybackHistoryResponse,
        PlaybackHistoryItem,
        TopArtistsResponse,
        TopTracksResponse,
        ArtistPlaybackStats,
    )
except ImportError:
    # Fallback for direct execution
    from logger import logger
    from browser_session import BrowserSession
    from utils import format_track_data, format_album_data, format_artist_data, bound_limit, format_recently_played_item, format_playback_history_item, _safe_get_attr
    from models import (
        LoginResponse,
        AuthStatusResponse,
        UserModel,
        TrackModel,
        TracksResponse,
        RecommendationsResponse,
        BatchRecommendationsRequest,
        BatchRecommendationsResponse,
        CreatePlaylistRequest,
        CreatePlaylistResponse,
        PlaylistModel,
        PlaylistsResponse,
        PlaylistTracksResponse,
        DeletePlaylistResponse,
        SearchResponse,
        SearchResultsModel,
        SearchTracksResponse,
        SearchAlbumsResponse,
        SearchArtistsResponse,
        RecentlyPlayedResponse,
        RecentlyPlayedItem,
        PlaybackHistoryResponse,
        PlaybackHistoryItem,
        TopArtistsResponse,
        TopTracksResponse,
        ArtistPlaybackStats,
    )


def configure_ssl_certificates() -> bool:
    """
    Configure SSL certificates, handling uv environment issues.
    
    Returns:
        True if configuration was successful, False otherwise
    """
    try:
        import certifi
        cert_path = certifi.where()
        
        # Verify the certificate file actually exists
        if os.path.exists(cert_path):
            # Set default SSL context to use certifi's certificate bundle
            ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=cert_path)
            # Also set environment variable for requests library
            os.environ['REQUESTS_CA_BUNDLE'] = cert_path
            os.environ['SSL_CERT_FILE'] = cert_path
            return True
        else:
            # Certificate file doesn't exist at expected path
            # Try to find certifi in the actual Python environment
            import site
            for site_packages in site.getsitepackages():
                potential_path = os.path.join(site_packages, 'certifi', 'cacert.pem')
                if os.path.exists(potential_path):
                    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=potential_path)
                    os.environ['REQUESTS_CA_BUNDLE'] = potential_path
                    os.environ['SSL_CERT_FILE'] = potential_path
                    logger.info(f"Using certifi from: {potential_path}")
                    return True
            
            # If we can't find certifi, use system certificates
            logger.warning(f"certifi certificate bundle not found at {cert_path}, using system certificates")
            ssl._create_default_https_context = ssl.create_default_context
            logger.info("Using system SSL certificates")
            return True
            
    except ImportError:
        # certifi not available, use system defaults
        logger.warning("certifi not available, using system SSL certificates")
        return False
    except Exception as e:
        logger.warning(f"Could not configure SSL certificates: {e}, using system defaults")
        return False


# Configure SSL before importing anything that uses HTTPS
configure_ssl_certificates()

# Initialize FastAPI app
app = FastAPI(
    title="TIDAL MCP API",
    version="0.1.0",
    description="REST API for TIDAL MCP functionality",
)


# ============================================================================
# Configuration and Dependencies
# ============================================================================

def get_session_file_path() -> Path:
    """
    Get the path to the TIDAL session file.
    
    Prefers user's home directory, falls back to temp directory.
    """
    home_dir = os.path.expanduser("~")
    config_dir = os.path.join(home_dir, ".tidal-mcp")
    
    # Create config directory if it doesn't exist
    try:
        os.makedirs(config_dir, exist_ok=True, mode=0o700)  # Private directory
        return Path(config_dir) / "session.json"
    except (OSError, PermissionError):
        # Fallback to temp directory if we can't create config directory
        temp_dir = tempfile.gettempdir()
        return Path(temp_dir) / "tidal-session-oauth.json"


SESSION_FILE = get_session_file_path()


def get_tidal_session() -> BrowserSession:
    """
    Dependency that provides an authenticated TIDAL session.
    
    Raises:
        HTTPException: If authentication fails or session file doesn't exist
    """
    if not SESSION_FILE.exists():
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Create session and load from file
    session = BrowserSession()
    login_success = session.login_session_file_auto(
        SESSION_FILE,
        fn_print=lambda msg: logger.info(f"TIDAL AUTH: {msg}")
    )
    
    if not login_success:
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    return session


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.get('/api/auth/login', response_model=LoginResponse)
async def login() -> LoginResponse:
    """
    Initiates the TIDAL authentication process.
    
    Automatically opens a browser for the user to login to their TIDAL account.
    """
    session = BrowserSession()
    
    def log_message(msg: str) -> None:
        logger.info(f"TIDAL AUTH: {msg}")
    
    try:
        login_success = session.login_session_file_auto(SESSION_FILE, fn_print=log_message)
        
        if login_success:
            return LoginResponse(
                status="success",
                message="Successfully authenticated with TIDAL",
                user_id=str(session.user.id) if session.user else None
            )
        else:
            raise HTTPException(status_code=401, detail="Authentication failed")
    
    except TimeoutError:
        raise HTTPException(status_code=408, detail="Authentication timed out")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get('/api/auth/status', response_model=AuthStatusResponse)
async def auth_status() -> AuthStatusResponse:
    """
    Check if there's an active authenticated session.
    """
    if not SESSION_FILE.exists():
        return AuthStatusResponse(
            authenticated=False,
            message="No session file found"
        )
    
    session = BrowserSession()
    login_success = session.login_session_file_auto(
        SESSION_FILE,
        fn_print=lambda msg: logger.debug(f"TIDAL AUTH: {msg}")
    )
    
    if login_success:
        user_info = UserModel(
            id=str(session.user.id),
            username=getattr(session.user, 'username', None) or "N/A",
            email=getattr(session.user, 'email', None) or "N/A"
        )
        
        return AuthStatusResponse(
            authenticated=True,
            message="Valid TIDAL session",
            user=user_info
        )
    else:
        return AuthStatusResponse(
            authenticated=False,
            message="Invalid or expired session"
        )


# ============================================================================
# Track Endpoints
# ============================================================================

@app.get('/api/tracks', response_model=TracksResponse)
async def get_tracks(
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of tracks to retrieve"),
    session: BrowserSession = Depends(get_tidal_session)
) -> TracksResponse:
    """
    Get tracks from the user's favorites.
    
    Args:
        limit: Maximum number of tracks to retrieve (1-50)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        favorites = session.user.favorites
        limit = bound_limit(limit)
        
        # Get tracks - handle both iterator and list cases
        try:
            tracks = favorites.tracks(limit=limit, order="DATE", order_direction="DESC")
            if hasattr(tracks, '__iter__') and not isinstance(tracks, (list, tuple, str)):
                tracks = list(tracks)
        except Exception as e:
            # Try without order parameters
            try:
                tracks = favorites.tracks(limit=limit)
                if hasattr(tracks, '__iter__') and not isinstance(tracks, (list, tuple, str)):
                    tracks = list(tracks)
            except Exception as e2:
                logger.error(f"Error fetching tracks: {e2} (original: {e})", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Error fetching tracks: {str(e2)}")
        
        # Format tracks with error handling
        track_list = []
        for track in tracks:
            try:
                track_list.append(format_track_data(track))
            except Exception as e:
                logger.warning(f"Error formatting track: {e}")
                continue

        return TracksResponse(tracks=track_list)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching tracks: {str(e)}")


@app.get('/api/recently_played', response_model=RecentlyPlayedResponse)
async def get_recently_played(
    limit: int = Query(default=50, ge=1, le=50, description="Maximum number of tracks to retrieve"),
    session: BrowserSession = Depends(get_tidal_session)
) -> RecentlyPlayedResponse:
    """
    Get the user's recently played tracks.
    
    Args:
        limit: Maximum number of tracks to retrieve (1-50, default: 50)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        limit = bound_limit(limit)
        
        # Try different methods to get recently played tracks
        # The TIDAL API might use different method names
        recently_played_tracks = []
        played_at_times = []
        
        try:
            # Try user.recently_played() if available
            if hasattr(session.user, 'recently_played'):
                recently_played_items = session.user.recently_played(limit=limit)
                if hasattr(recently_played_items, '__iter__') and not isinstance(recently_played_items, (list, tuple, str)):
                    recently_played_items = list(recently_played_items)
                
                for item in recently_played_items:
                    # Handle different possible structures
                    if hasattr(item, 'track'):
                        track = item.track
                        played_at = getattr(item, 'played_at', None) or getattr(item, 'timestamp', None)
                    elif hasattr(item, 'id'):
                        track = item
                        played_at = getattr(item, 'played_at', None) or getattr(item, 'timestamp', None)
                    else:
                        track = item
                        played_at = None
                    
                    recently_played_tracks.append(track)
                    played_at_times.append(played_at)
            # Try user.history() if available
            elif hasattr(session.user, 'history'):
                recently_played_items = session.user.history(limit=limit)
                if hasattr(recently_played_items, '__iter__') and not isinstance(recently_played_items, (list, tuple, str)):
                    recently_played_items = list(recently_played_items)
                
                for item in recently_played_items:
                    if hasattr(item, 'track'):
                        track = item.track
                        played_at = getattr(item, 'played_at', None) or getattr(item, 'timestamp', None)
                    elif hasattr(item, 'id'):
                        track = item
                        played_at = getattr(item, 'played_at', None) or getattr(item, 'timestamp', None)
                    else:
                        track = item
                        played_at = None
                    
                    recently_played_tracks.append(track)
                    played_at_times.append(played_at)
            # Try session.get_recently_played() if available
            elif hasattr(session, 'get_recently_played'):
                recently_played_items = session.get_recently_played(limit=limit)
                if hasattr(recently_played_items, '__iter__') and not isinstance(recently_played_items, (list, tuple, str)):
                    recently_played_items = list(recently_played_items)
                
                for item in recently_played_items:
                    if hasattr(item, 'track'):
                        track = item.track
                        played_at = getattr(item, 'played_at', None) or getattr(item, 'timestamp', None)
                    elif hasattr(item, 'id'):
                        track = item
                        played_at = getattr(item, 'played_at', None) or getattr(item, 'timestamp', None)
                    else:
                        track = item
                        played_at = None
                    
                    recently_played_tracks.append(track)
                    played_at_times.append(played_at)
            else:
                # Fallback: try to access via user attributes
                # Some APIs store recently played in user attributes
                if hasattr(session.user, 'recent_tracks'):
                    recently_played_tracks = session.user.recent_tracks(limit=limit)
                    if hasattr(recently_played_tracks, '__iter__') and not isinstance(recently_played_tracks, (list, tuple, str)):
                        recently_played_tracks = list(recently_played_tracks)
                    played_at_times = [None] * len(recently_played_tracks)
                else:
                    raise AttributeError("Recently played tracks not available - no suitable method found")
        except AttributeError as e:
            logger.warning(f"Recently played method not found: {e}")
            # If no specific recently played method, we might need to use a different approach
            # For now, return empty list with a message
            raise HTTPException(
                status_code=501,
                detail="Recently played tracks are not available through the TIDAL API. This feature may require a different API endpoint."
            )
        except Exception as e:
            logger.error(f"Error fetching recently played tracks: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching recently played tracks: {str(e)}")
        
        # Format tracks with timestamps
        recently_played_list = []
        for i, track in enumerate(recently_played_tracks):
            try:
                played_at = played_at_times[i] if i < len(played_at_times) else None
                recently_played_list.append(format_recently_played_item(track, played_at=played_at))
            except Exception as e:
                logger.warning(f"Error formatting recently played track: {e}")
                continue

        return RecentlyPlayedResponse(tracks=recently_played_list, total=len(recently_played_list))
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_recently_played: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching recently played tracks: {str(e)}")


# ============================================================================
# Playback History Endpoints
# ============================================================================

@app.get('/api/playback_history', response_model=PlaybackHistoryResponse)
async def get_playback_history(
    limit: Optional[int] = Query(default=None, ge=1, le=1000, description="Maximum number of tracks to retrieve (default: all)"),
    years_back: Optional[int] = Query(default=None, ge=1, le=10, description="Number of years back to retrieve history"),
    date_from: Optional[str] = Query(default=None, description="Start date (ISO format: YYYY-MM-DD)"),
    date_to: Optional[str] = Query(default=None, description="End date (ISO format: YYYY-MM-DD)"),
    session: BrowserSession = Depends(get_tidal_session)
) -> PlaybackHistoryResponse:
    """
    Get the user's full playback history with play counts.
    
    Args:
        limit: Maximum number of tracks to retrieve (default: all available)
        years_back: Number of years back to retrieve history (e.g., 2 for last 2 years)
        date_from: Start date in ISO format (YYYY-MM-DD)
        date_to: End date in ISO format (YYYY-MM-DD)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        from collections import defaultdict
        
        # Parse date filters
        date_from_dt = None
        date_to_dt = None
        
        if years_back:
            date_from_dt = datetime.now() - timedelta(days=years_back * 365)
            date_to_dt = datetime.now()
        else:
            if date_from:
                try:
                    date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid date_from format: {date_from}. Use YYYY-MM-DD")
            if date_to:
                try:
                    date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid date_to format: {date_to}. Use YYYY-MM-DD")
        
        # Try to get playback history from TIDAL API
        # The API might provide this through different methods
        history_items = []
        
        try:
            # Try user.playback_history() if available
            if hasattr(session.user, 'playback_history'):
                raw_history = session.user.playback_history(limit=limit or 10000)
                if hasattr(raw_history, '__iter__') and not isinstance(raw_history, (list, tuple, str)):
                    raw_history = list(raw_history)
                history_items = raw_history
            # Try user.history() with larger limit for full history
            elif hasattr(session.user, 'history'):
                raw_history = session.user.history(limit=limit or 10000)
                if hasattr(raw_history, '__iter__') and not isinstance(raw_history, (list, tuple, str)):
                    raw_history = list(raw_history)
                history_items = raw_history
            else:
                raise AttributeError("Playback history not available - no suitable method found")
        except AttributeError as e:
            logger.warning(f"Playback history method not found: {e}")
            raise HTTPException(
                status_code=501,
                detail="Playback history is not available through the TIDAL API. This feature may require a different API endpoint."
            )
        except Exception as e:
            logger.error(f"Error fetching playback history: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error fetching playback history: {str(e)}")
        
        # Aggregate tracks by ID to count plays
        track_plays = defaultdict(lambda: {'track': None, 'play_count': 0, 'first_played': None, 'last_played': None})
        
        for item in history_items:
            # Extract track and timestamp
            if hasattr(item, 'track'):
                track = item.track
                played_at = getattr(item, 'played_at', None) or getattr(item, 'timestamp', None)
            elif hasattr(item, 'id'):
                track = item
                played_at = getattr(item, 'played_at', None) or getattr(item, 'timestamp', None)
            else:
                continue
            
            # Filter by date if specified
            if played_at and date_from_dt and played_at < date_from_dt:
                continue
            if played_at and date_to_dt and played_at > date_to_dt:
                continue
            
            track_id = str(_safe_get_attr(track, 'id', ''))
            if not track_id:
                continue
            
            if track_plays[track_id]['track'] is None:
                track_plays[track_id]['track'] = track
            
            track_plays[track_id]['play_count'] += 1
            
            if played_at:
                if track_plays[track_id]['first_played'] is None or played_at < track_plays[track_id]['first_played']:
                    track_plays[track_id]['first_played'] = played_at
                if track_plays[track_id]['last_played'] is None or played_at > track_plays[track_id]['last_played']:
                    track_plays[track_id]['last_played'] = played_at
        
        # Format history items
        history_list = []
        total_plays = 0
        
        for track_id, data in track_plays.items():
            try:
                history_item = format_playback_history_item(
                    data['track'],
                    play_count=data['play_count'],
                    first_played=data['first_played'],
                    last_played=data['last_played']
                )
                history_list.append(history_item)
                total_plays += data['play_count']
            except Exception as e:
                logger.warning(f"Error formatting playback history track: {e}")
                continue
        
        # Sort by play count descending
        history_list.sort(key=lambda x: x.play_count, reverse=True)
        
        # Apply limit if specified
        if limit:
            history_list = history_list[:limit]
        
        return PlaybackHistoryResponse(
            tracks=history_list,
            total_tracks=len(history_list),
            total_plays=total_plays,
            date_from=date_from_dt,
            date_to=date_to_dt
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_playback_history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching playback history: {str(e)}")


@app.get('/api/playback_history/top_artists', response_model=TopArtistsResponse)
async def get_top_artists(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of artists to retrieve"),
    years_back: Optional[int] = Query(default=None, ge=1, le=10, description="Number of years back to analyze"),
    date_from: Optional[str] = Query(default=None, description="Start date (ISO format: YYYY-MM-DD)"),
    date_to: Optional[str] = Query(default=None, description="End date (ISO format: YYYY-MM-DD)"),
    session: BrowserSession = Depends(get_tidal_session)
) -> TopArtistsResponse:
    """
    Get the user's top artists based on playback history.
    
    Args:
        limit: Maximum number of artists to retrieve (1-100, default: 50)
        years_back: Number of years back to analyze (e.g., 2 for last 2 years)
        date_from: Start date in ISO format (YYYY-MM-DD)
        date_to: End date in ISO format (YYYY-MM-DD)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        from collections import defaultdict
        
        # Parse date filters
        date_from_dt = None
        date_to_dt = None
        
        if years_back:
            date_from_dt = datetime.now() - timedelta(days=years_back * 365)
            date_to_dt = datetime.now()
        else:
            if date_from:
                try:
                    date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid date_from format: {date_from}. Use YYYY-MM-DD")
            if date_to:
                try:
                    date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid date_to format: {date_to}. Use YYYY-MM-DD")
        
        # Get playback history
        history_response = await get_playback_history(
            limit=None,  # Get all for aggregation
            years_back=years_back,
            date_from=date_from,
            date_to=date_to,
            session=session
        )
        
        # Aggregate by artist
        artist_stats = defaultdict(lambda: {'artist_id': None, 'artist_name': '', 'play_count': 0, 'track_count': 0, 'total_duration': 0})
        
        for track_item in history_response.tracks:
            artist_name = track_item.artist
            if not artist_name or artist_name == "Unknown":
                continue
            
            artist_stats[artist_name]['artist_name'] = artist_name
            artist_stats[artist_name]['play_count'] += track_item.play_count
            artist_stats[artist_name]['track_count'] += 1
            artist_stats[artist_name]['total_duration'] += track_item.duration * track_item.play_count
        
        # Convert to list and sort by play count
        artists_list = []
        for artist_name, stats in artist_stats.items():
            # Try to get artist ID from first track with this artist
            # This is a simplified approach - in practice, you'd want to look up the artist
            artist_id = None
            artist_url = None
            if stats['artist_id']:
                artist_id = stats['artist_id']
                artist_url = f"https://tidal.com/browse/artist/{artist_id}?u"
            
            artists_list.append(ArtistPlaybackStats(
                artist_id=artist_id,
                artist_name=artist_name,
                url=artist_url,
                play_count=stats['play_count'],
                track_count=stats['track_count'],
                total_duration=stats['total_duration']
            ))
        
        # Sort by play count descending
        artists_list.sort(key=lambda x: x.play_count, reverse=True)
        
        # Apply limit
        limit = bound_limit(limit, max_n=100)
        artists_list = artists_list[:limit]
        
        return TopArtistsResponse(
            artists=artists_list,
            total=len(artists_list),
            date_from=date_from_dt,
            date_to=date_to_dt
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_top_artists: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching top artists: {str(e)}")


@app.get('/api/playback_history/top_tracks', response_model=TopTracksResponse)
async def get_top_tracks(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of tracks to retrieve"),
    years_back: Optional[int] = Query(default=None, ge=1, le=10, description="Number of years back to analyze"),
    date_from: Optional[str] = Query(default=None, description="Start date (ISO format: YYYY-MM-DD)"),
    date_to: Optional[str] = Query(default=None, description="End date (ISO format: YYYY-MM-DD)"),
    session: BrowserSession = Depends(get_tidal_session)
) -> TopTracksResponse:
    """
    Get the user's top tracks based on playback history.
    
    Args:
        limit: Maximum number of tracks to retrieve (1-100, default: 50)
        years_back: Number of years back to analyze (e.g., 2 for last 2 years)
        date_from: Start date in ISO format (YYYY-MM-DD)
        date_to: End date in ISO format (YYYY-MM-DD)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        # Get playback history
        history_response = await get_playback_history(
            limit=limit,
            years_back=years_back,
            date_from=date_from,
            date_to=date_to,
            session=session
        )
        
        # Tracks are already sorted by play count from get_playback_history
        limit = bound_limit(limit, max_n=100)
        top_tracks = history_response.tracks[:limit]
        
        return TopTracksResponse(
            tracks=top_tracks,
            total=len(top_tracks),
            date_from=history_response.date_from,
            date_to=history_response.date_to
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_top_tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching top tracks: {str(e)}")


@app.get('/api/recommendations/track/{track_id}', response_model=RecommendationsResponse)
async def get_track_recommendations(
    track_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of recommendations"),
    session: BrowserSession = Depends(get_tidal_session)
) -> RecommendationsResponse:
    """
    Get recommended tracks based on a specific track using TIDAL's track radio feature.
    
    Args:
        track_id: TIDAL track ID
        limit: Maximum number of recommendations (1-50)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        limit = bound_limit(limit)
        
        track = session.track(track_id)
        if not track:
            raise HTTPException(status_code=404, detail=f"Track with ID {track_id} not found")
        
        recommendations = track.get_track_radio(limit=limit)
        track_list = [format_track_data(track) for track in recommendations]
        
        return RecommendationsResponse(recommendations=track_list)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting track recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching recommendations: {str(e)}")


@app.post('/api/recommendations/batch', response_model=BatchRecommendationsResponse)
async def get_batch_recommendations(
    request_data: BatchRecommendationsRequest,
    session: BrowserSession = Depends(get_tidal_session)
) -> BatchRecommendationsResponse:
    """
    Get recommended tracks based on a list of track IDs using concurrent requests.
    
    Args:
        request_data: Batch recommendations request with track IDs and options
        session: Authenticated TIDAL session (dependency)
    """
    try:
        track_ids = request_data.track_ids
        limit_per_track = bound_limit(request_data.limit_per_track)
        remove_duplicates = request_data.remove_duplicates
        
        def get_track_recommendations(track_id: str) -> List[TrackModel]:
            """Get recommendations for a single track."""
            try:
                track = session.track(track_id)
                recommendations = track.get_track_radio(limit=limit_per_track)
                return [
                    format_track_data(rec, source_track_id=track_id)
                    for rec in recommendations
                ]
            except Exception as e:
                logger.warning(f"Error getting recommendations for track {track_id}: {str(e)}")
                return []
        
        all_recommendations = []
        seen_track_ids = set()
        
        # Use ThreadPoolExecutor to process tracks concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(track_ids)) as executor:
            future_to_track_id = {
                executor.submit(get_track_recommendations, track_id): track_id
                for track_id in track_ids
            }
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_track_id):
                track_recommendations = future.result()
                
                for track_data in track_recommendations:
                    track_id = track_data.id
                    
                    # Skip if we've already seen this track and want to remove duplicates
                    if remove_duplicates and track_id and track_id in seen_track_ids:
                        continue
                    
                    all_recommendations.append(track_data)
                    if track_id:
                        seen_track_ids.add(track_id)
        
        return BatchRecommendationsResponse(recommendations=all_recommendations)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching batch recommendations: {str(e)}")


# ============================================================================
# Playlist Endpoints
# ============================================================================

@app.post('/api/playlists', response_model=CreatePlaylistResponse)
async def create_playlist(
    request_data: CreatePlaylistRequest,
    session: BrowserSession = Depends(get_tidal_session)
) -> CreatePlaylistResponse:
    """
    Creates a new TIDAL playlist and adds tracks to it.
    
    Args:
        request_data: Playlist creation request with title, description, and track IDs
        session: Authenticated TIDAL session (dependency)
    """
    try:
        playlist = session.user.create_playlist(request_data.title, request_data.description)
        playlist.add(request_data.track_ids)
        
        playlist_info = PlaylistModel(
            id=str(playlist.id),
            title=playlist.name,
            description=getattr(playlist, 'description', '') or '',
            created=getattr(playlist, 'created', None),
            last_updated=getattr(playlist, 'last_updated', None),
            track_count=getattr(playlist, 'num_tracks', 0) or 0,
            duration=getattr(playlist, 'duration', 0) or 0,
            url=f"https://tidal.com/playlist/{playlist.id}"
        )
        
        return CreatePlaylistResponse(
            status="success",
            message=f"Playlist '{request_data.title}' created successfully with {len(request_data.track_ids)} tracks",
            playlist=playlist_info
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating playlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating playlist: {str(e)}")


@app.get('/api/playlists', response_model=PlaylistsResponse)
async def get_user_playlists(
    session: BrowserSession = Depends(get_tidal_session)
) -> PlaylistsResponse:
    """
    Get the user's playlists from TIDAL.
    
    Args:
        session: Authenticated TIDAL session (dependency)
    """
    try:
        playlists = session.user.playlists()
        
        playlist_list = []
        for playlist in playlists:
            playlist_info = PlaylistModel(
                id=str(playlist.id),
                title=playlist.name,
                description=getattr(playlist, 'description', '') or '',
                created=getattr(playlist, 'created', None),
                last_updated=getattr(playlist, 'last_updated', None),
                track_count=getattr(playlist, 'num_tracks', 0) or 0,
                duration=getattr(playlist, 'duration', 0) or 0,
                url=f"https://tidal.com/playlist/{playlist.id}"
            )
            playlist_list.append(playlist_info)
        
        # Sort playlists by last_updated in descending order
        sorted_playlists = sorted(
            playlist_list,
            key=lambda x: x.last_updated or '',
            reverse=True
        )

        return PlaylistsResponse(playlists=sorted_playlists)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching playlists: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching playlists: {str(e)}")


@app.get('/api/playlists/{playlist_id}/tracks', response_model=PlaylistTracksResponse)
async def get_playlist_tracks(
    playlist_id: str,
    limit: int = Query(default=100, ge=1, le=100, description="Maximum number of tracks to retrieve"),
    session: BrowserSession = Depends(get_tidal_session)
) -> PlaylistTracksResponse:
    """
    Get tracks from a specific TIDAL playlist.
    
    Args:
        playlist_id: TIDAL playlist ID
        limit: Maximum number of tracks to retrieve (1-100)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        limit = bound_limit(limit, max_n=100)
        
        playlist = session.playlist(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail=f"Playlist with ID {playlist_id} not found")
        
        tracks = playlist.items(limit=limit)
        track_list = [format_track_data(track) for track in tracks]
        
        return PlaylistTracksResponse(
            playlist_id=str(playlist.id),
            tracks=track_list,
            total_tracks=len(track_list)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching playlist tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error fetching playlist tracks: {str(e)}")


@app.delete('/api/playlists/{playlist_id}', response_model=DeletePlaylistResponse)
async def delete_playlist(
    playlist_id: str,
    session: BrowserSession = Depends(get_tidal_session)
) -> DeletePlaylistResponse:
    """
    Delete a TIDAL playlist by its ID.
    
    Args:
        playlist_id: TIDAL playlist ID
        session: Authenticated TIDAL session (dependency)
    """
    try:
        playlist = session.playlist(playlist_id)
        if not playlist:
            raise HTTPException(status_code=404, detail=f"Playlist with ID {playlist_id} not found")
        
        playlist.delete()
        
        return DeletePlaylistResponse(
            status="success",
            message=f"Playlist with ID {playlist_id} was successfully deleted"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error deleting playlist: {str(e)}")


# ============================================================================
# Search Endpoints
# ============================================================================

@app.get('/api/search', response_model=SearchResponse)
async def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, ge=1, le=50, description="Maximum number of results per type"),
    types: str = Query(default="tracks,albums,artists", description="Comma-separated list of types to search"),
    session: BrowserSession = Depends(get_tidal_session)
) -> SearchResponse:
    """
    Search for tracks, albums, and artists on TIDAL.
    
    Args:
        q: Search query string
        limit: Maximum number of results per type (1-50)
        types: Comma-separated list of types (tracks, albums, artists)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        import tidalapi
        
        limit = bound_limit(limit)
        types_list = [t.strip().lower() for t in types.split(',')]
        
        # Determine which models to search
        models = []
        if 'tracks' in types_list:
            models.append(tidalapi.Track)
        if 'albums' in types_list:
            models.append(tidalapi.Album)
        if 'artists' in types_list:
            models.append(tidalapi.Artist)
        
        if not models:
            raise HTTPException(
                status_code=400,
                detail="Invalid types. Must include at least one of: tracks, albums, artists"
            )
        
        # Perform search
        results = session.search(q, models=models, limit=limit)
        
        # Format results
        formatted_results = SearchResultsModel()
        
        if 'tracks' in types_list and 'tracks' in results:
            formatted_results.tracks = [format_track_data(track) for track in results['tracks']]
        
        if 'albums' in types_list and 'albums' in results:
            formatted_results.albums = [format_album_data(album) for album in results['albums']]
        
        if 'artists' in types_list and 'artists' in results:
            formatted_results.artists = [format_artist_data(artist) for artist in results['artists']]
        
        return SearchResponse(
            query=q,
            results=formatted_results,
            total_tracks=len(formatted_results.tracks),
            total_albums=len(formatted_results.albums),
            total_artists=len(formatted_results.artists)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error performing search: {str(e)}")


@app.get('/api/search/tracks', response_model=SearchTracksResponse)
async def search_tracks(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, ge=1, le=50, description="Maximum number of results"),
    session: BrowserSession = Depends(get_tidal_session)
) -> SearchTracksResponse:
    """
    Search for tracks on TIDAL.
    
    Args:
        q: Search query string
        limit: Maximum number of results (1-50)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        import tidalapi
        
        limit = bound_limit(limit)
        results = session.search(q, models=[tidalapi.Track], limit=limit)
        
        tracks = results.get('tracks', [])
        formatted_tracks = [format_track_data(track) for track in tracks]
        
        return SearchTracksResponse(
            query=q,
            tracks=formatted_tracks,
            total=len(formatted_tracks)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching tracks: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching tracks: {str(e)}")


@app.get('/api/search/albums', response_model=SearchAlbumsResponse)
async def search_albums(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, ge=1, le=50, description="Maximum number of results"),
    session: BrowserSession = Depends(get_tidal_session)
) -> SearchAlbumsResponse:
    """
    Search for albums on TIDAL.
    
    Args:
        q: Search query string
        limit: Maximum number of results (1-50)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        import tidalapi
        
        limit = bound_limit(limit)
        results = session.search(q, models=[tidalapi.Album], limit=limit)
        
        albums = results.get('albums', [])
        formatted_albums = [format_album_data(album) for album in albums]
        
        return SearchAlbumsResponse(
            query=q,
            albums=formatted_albums,
            total=len(formatted_albums)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching albums: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching albums: {str(e)}")


@app.get('/api/search/artists', response_model=SearchArtistsResponse)
async def search_artists(
    q: str = Query(..., description="Search query"),
    limit: int = Query(default=20, ge=1, le=50, description="Maximum number of results"),
    session: BrowserSession = Depends(get_tidal_session)
) -> SearchArtistsResponse:
    """
    Search for artists on TIDAL.
    
    Args:
        q: Search query string
        limit: Maximum number of results (1-50)
        session: Authenticated TIDAL session (dependency)
    """
    try:
        import tidalapi
        
        limit = bound_limit(limit)
        results = session.search(q, models=[tidalapi.Artist], limit=limit)
        
        artists = results.get('artists', [])
        formatted_artists = [format_artist_data(artist) for artist in artists]
        
        return SearchArtistsResponse(
            query=q,
            artists=formatted_artists,
            total=len(formatted_artists)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching artists: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error searching artists: {str(e)}")


# ============================================================================
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    import uvicorn
    
    # Add parent directory to path for imports when running directly
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Get port from environment variable or use default
    port = int(os.environ.get("TIDAL_MCP_PORT", 5050))
    
    logger.info(f"Starting FastAPI app on port {port}")
    uvicorn.run(app, host="127.0.0.1", port=port, log_config=None)
