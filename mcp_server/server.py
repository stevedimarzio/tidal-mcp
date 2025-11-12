from mcp.server.fastmcp import FastMCP
import requests
import atexit
import sys
from pathlib import Path

from typing import Optional, List

# Handle logger import for both module and direct execution
try:
    from .logger import logger
except ImportError:
    # Fallback for direct execution - add parent directory to path
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    from mcp_server.logger import logger

from .utils import start_fastapi_app, shutdown_fastapi_app, FASTAPI_APP_URL, FASTAPI_PORT

# Print the port being used for debugging
print(f"TIDAL MCP starting on port {FASTAPI_PORT}")

# Create an MCP server
mcp = FastMCP("TIDAL MCP")

# Start the FastAPI app when this script is loaded
logger.info("MCP server module is being loaded. Starting FastAPI app...")
start_fastapi_app()

# Register the shutdown function to be called when the MCP server exits
atexit.register(shutdown_fastapi_app)

@mcp.tool()
def tidal_login() -> dict:
    """
    Authenticate with TIDAL through browser login flow.
    This will open a browser window for the user to log in to their TIDAL account.
    
    Returns:
        A dictionary containing authentication status and user information if successful
    """
    try:
        # Call your FastAPI endpoint for TIDAL authentication
        response = requests.get(f"{FASTAPI_APP_URL}/api/auth/login")
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Authentication failed: {error_data.get('message', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL authentication service: {str(e)}"
        }
    
@mcp.tool()
def get_favorite_tracks(limit: int = 20) -> dict:
    """
    Retrieves tracks from the user's TIDAL account favorites.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "What are my favorite tracks?"
    - "Show me my TIDAL favorites"
    - "What music do I have saved?"
    - "Get my favorite songs"
    - Any request to view their saved/favorite tracks
    
    This function retrieves the user's favorite tracks from TIDAL.
    
    Args:
        limit: Maximum number of tracks to retrieve (default: 20, note it should be large enough by default unless specified otherwise).
    
    Returns:
        A dictionary containing track information including track ID, title, artist, album, and duration.
        Returns an error message if not authenticated or if retrieval fails.
    """
    try:
        # First, check if the user is authenticated
        auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
        auth_data = auth_check.json()
        
        if not auth_data.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first before I can fetch your favorite tracks. Please use the tidal_login() function."
            }
            
        # Call your FastAPI endpoint to retrieve tracks with the specified limit
        response = requests.get(f"{FASTAPI_APP_URL}/api/tracks", params={"limit": limit})
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to retrieve tracks: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL tracks service: {str(e)}"
        }

@mcp.tool()
def get_recently_played(limit: int = 50) -> dict:
    """
    Retrieves the user's recently played tracks from their TIDAL account.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "What have I been listening to?"
    - "Show me my recently played tracks"
    - "What songs did I recently play?"
    - "Get my recently played tracks"
    - "Show me my recent listening activity"
    - Any request to view their recently played tracks
    
    This function retrieves the user's recently played tracks from TIDAL.
    
    Args:
        limit: Maximum number of tracks to retrieve (default: 50, max: 50)
    
    Returns:
        A dictionary containing track information including track ID, title, artist, album, duration, and when it was played.
        Returns an error message if not authenticated or if retrieval fails.
    """
    try:
        # First, check if the user is authenticated
        auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
        auth_data = auth_check.json()
        
        if not auth_data.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first before I can fetch your recently played tracks. Please use the tidal_login() function."
            }
            
        # Call your FastAPI endpoint to retrieve recently played tracks with the specified limit
        response = requests.get(f"{FASTAPI_APP_URL}/api/recently_played", params={"limit": limit})
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        elif response.status_code == 501:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Recently played tracks are not available: {error_data.get('detail', 'This feature may not be supported by the TIDAL API.')}"
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to retrieve recently played tracks: {error_data.get('detail', error_data.get('error', 'Unknown error'))}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL recently played service: {str(e)}"
        }

@mcp.tool()
def get_playback_history(limit: Optional[int] = None, years_back: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> dict:
    """
    Retrieves the user's full playback history with play counts from their TIDAL account.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Show me my listening history"
    - "What have I listened to in the last 2 years?"
    - "Get my playback history"
    - "Show me all the tracks I've played"
    - Any request to view their full listening history with play counts
    
    This function retrieves the user's complete playback history from TIDAL, including play counts and timestamps.
    
    Args:
        limit: Maximum number of tracks to retrieve (default: all available, max: 1000)
        years_back: Number of years back to retrieve history (e.g., 2 for last 2 years, max: 10)
        date_from: Start date in ISO format (YYYY-MM-DD)
        date_to: End date in ISO format (YYYY-MM-DD)
    
    Returns:
        A dictionary containing track information with play counts, first played, and last played timestamps.
        Returns an error message if not authenticated or if retrieval fails.
    """
    try:
        # First, check if the user is authenticated
        auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
        auth_data = auth_check.json()
        
        if not auth_data.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first before I can fetch your playback history. Please use the tidal_login() function."
            }
        
        # Build query parameters
        params = {}
        if limit is not None:
            params["limit"] = limit
        if years_back is not None:
            params["years_back"] = years_back
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
            
        # Call your FastAPI endpoint to retrieve playback history
        response = requests.get(f"{FASTAPI_APP_URL}/api/playback_history", params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        elif response.status_code == 501:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Playback history is not available: {error_data.get('detail', 'This feature may not be supported by the TIDAL API.')}"
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to retrieve playback history: {error_data.get('detail', error_data.get('error', 'Unknown error'))}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL playback history service: {str(e)}"
        }

@mcp.tool()
def get_top_artists(limit: int = 50, years_back: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> dict:
    """
    Retrieves the user's top artists based on playback history from their TIDAL account.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Show me my most listened artists"
    - "Who are my top artists in the last 2 years?"
    - "What artists do I listen to the most?"
    - "Get my top artists"
    - Any request to view their most listened artists
    
    This function retrieves the user's top artists based on playback history, aggregated by play count.
    
    Args:
        limit: Maximum number of artists to retrieve (default: 50, max: 100)
        years_back: Number of years back to analyze (e.g., 2 for last 2 years, max: 10)
        date_from: Start date in ISO format (YYYY-MM-DD)
        date_to: End date in ISO format (YYYY-MM-DD)
    
    Returns:
        A dictionary containing artist statistics including play count, track count, and total duration.
        Returns an error message if not authenticated or if retrieval fails.
    """
    try:
        # First, check if the user is authenticated
        auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
        auth_data = auth_check.json()
        
        if not auth_data.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first before I can fetch your top artists. Please use the tidal_login() function."
            }
        
        # Build query parameters
        params = {"limit": limit}
        if years_back is not None:
            params["years_back"] = years_back
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
            
        # Call your FastAPI endpoint to retrieve top artists
        response = requests.get(f"{FASTAPI_APP_URL}/api/playback_history/top_artists", params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        elif response.status_code == 501:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Top artists are not available: {error_data.get('detail', 'This feature may not be supported by the TIDAL API.')}"
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to retrieve top artists: {error_data.get('detail', error_data.get('error', 'Unknown error'))}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL top artists service: {str(e)}"
        }

@mcp.tool()
def get_top_tracks(limit: int = 50, years_back: Optional[int] = None, date_from: Optional[str] = None, date_to: Optional[str] = None) -> dict:
    """
    Retrieves the user's top tracks based on playback history from their TIDAL account.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Show me my most listened tracks"
    - "What are my top tracks in the last 2 years?"
    - "What songs do I listen to the most?"
    - "Get my top tracks"
    - Any request to view their most listened tracks
    
    This function retrieves the user's top tracks based on playback history, sorted by play count.
    
    Args:
        limit: Maximum number of tracks to retrieve (default: 50, max: 100)
        years_back: Number of years back to analyze (e.g., 2 for last 2 years, max: 10)
        date_from: Start date in ISO format (YYYY-MM-DD)
        date_to: End date in ISO format (YYYY-MM-DD)
    
    Returns:
        A dictionary containing track information with play counts, sorted by most played.
        Returns an error message if not authenticated or if retrieval fails.
    """
    try:
        # First, check if the user is authenticated
        auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
        auth_data = auth_check.json()
        
        if not auth_data.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first before I can fetch your top tracks. Please use the tidal_login() function."
            }
        
        # Build query parameters
        params = {"limit": limit}
        if years_back is not None:
            params["years_back"] = years_back
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
            
        # Call your FastAPI endpoint to retrieve top tracks
        response = requests.get(f"{FASTAPI_APP_URL}/api/playback_history/top_tracks", params=params)
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        elif response.status_code == 501:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Top tracks are not available: {error_data.get('detail', 'This feature may not be supported by the TIDAL API.')}"
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to retrieve top tracks: {error_data.get('detail', error_data.get('error', 'Unknown error'))}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL top tracks service: {str(e)}"
        }
    
def _get_tidal_recommendations(track_ids: list = None, limit_per_track: int = 20, filter_criteria: str = None) -> dict:
    """
    [INTERNAL USE] Gets raw recommendation data from TIDAL API.
    This is a lower-level function primarily used by higher-level recommendation functions.
    For end-user recommendations, use recommend_tracks instead.
    
    Args:
        track_ids: List of TIDAL track IDs to use as seeds for recommendations.
        limit_per_track: Maximum number of recommendations to get per track (default: 20)
        filter_criteria: Optional string describing criteria to filter recommendations
                         (e.g., "relaxing", "new releases", "upbeat")
    
    Returns:
        A dictionary containing recommended tracks based on seed tracks and filtering criteria.
    """
    try:        
        # Validate track_ids
        if not track_ids or not isinstance(track_ids, list) or len(track_ids) == 0:
            return {
                "status": "error",
                "message": "No track IDs provided for recommendations."
            }
                
        # Call the batch recommendations endpoint
        payload = {
            "track_ids": track_ids,
            "limit_per_track": limit_per_track,
            "remove_duplicates": True
        }
        
        response = requests.post(f"{FASTAPI_APP_URL}/api/recommendations/batch", json=payload)
        
        if response.status_code != 200:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to get recommendations: {error_data.get('error', 'Unknown error')}"
            }
        
        recommendations = response.json().get("recommendations", [])
        
        # If filter criteria is provided, include it in the response for LLM processing
        result = {
            "recommendations": recommendations,
            "total_count": len(recommendations)
        }
        
        if filter_criteria:
            result["filter_criteria"] = filter_criteria
            
        return result
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to get recommendations: {str(e)}"
        }
    
@mcp.tool()
def recommend_tracks(track_ids: Optional[List[str]] = None, filter_criteria: Optional[str] = None, limit_per_track: int = 20, limit_from_favorite: int = 20) -> dict:
    """
    Recommends music tracks based on specified track IDs or can use the user's TIDAL favorites if no IDs are provided.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - Music recommendations
    - Track suggestions
    - Music similar to their TIDAL favorites or specific tracks
    - "What should I listen to?"
    - Any request to recommend songs/tracks/music based on their TIDAL history or specific tracks
    
    This function gets recommendations based on provided track IDs or retrieves the user's 
    favorite tracks as seeds if no IDs are specified.
    
    When processing the results of this tool:
    1. Analyze the seed tracks to understand the music taste or direction
    2. Review the recommended tracks from TIDAL
    3. IMPORTANT: Do NOT include any tracks from the seed tracks in your recommendations
    4. Ensure there are NO DUPLICATES in your recommended tracks list
    5. Select and rank the most appropriate tracks based on the seed tracks and filter criteria
    6. Group recommendations by similar styles, artists, or moods with descriptive headings
    7. For each recommended track, provide:
       - The track name, artist, album
       - Always include the track's URL to make it easy for users to listen to the track
       - A brief explanation of why this track might appeal to the user based on the seed tracks
       - If applicable, how this track matches their specific filter criteria       
    8. Format your response as a nicely presented list of recommendations with helpful context (remember to include the track's URL!)
    9. Begin with a brief introduction explaining your selection strategy
    10. Lastly, unless specified otherwise, you should recommend MINIMUM 20 tracks (or more if possible) to give the user a good variety to choose from.
    
    [IMPORTANT NOTE] If you're not familiar with any artists or tracks mentioned, you should use internet search capabilities if available to provide more accurate information.
    
    Args:
        track_ids: Optional list of TIDAL track IDs to use as seeds for recommendations.
                  If not provided, will use the user's favorite tracks.
        filter_criteria: Specific preferences for filtering recommendations (e.g., "relaxing music," 
                         "recent releases," "upbeat," "jazz influences")
        limit_per_track: Maximum number of recommendations to get per track (NOTE: default: 20, unless specified otherwise, we'd like to keep the default large enough to have enough candidates to work with)
        limit_from_favorite: Maximum number of favorite tracks to use as seeds (NOTE: default: 20, unless specified otherwise, we'd like to keep the default large enough to have enough candidates to work with)
        
    Returns:
        A dictionary containing both the seed tracks and recommended tracks
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before I can recommend music. Please use the tidal_login() function."
        }
    
    # Initialize variables to store our seed tracks and their info
    seed_track_ids = []
    seed_tracks_info = []
    
    # If track_ids are provided, use them directly
    if track_ids and isinstance(track_ids, list) and len(track_ids) > 0:
        seed_track_ids = track_ids
        # Note: We don't have detailed info about these tracks, just IDs
        # This is fine as the recommendation API only needs IDs
    else:
        # If no track_ids provided, get the user's favorite tracks
        tracks_response = get_favorite_tracks(limit=limit_from_favorite)
        
        # Check if we successfully retrieved tracks
        if "status" in tracks_response and tracks_response["status"] == "error":
            return {
                "status": "error",
                "message": f"Unable to get favorite tracks for recommendations: {tracks_response['message']}"
            }
        
        # Extract the track data
        favorite_tracks = tracks_response.get("tracks", [])
        
        if not favorite_tracks:
            return {
                "status": "error",
                "message": "I couldn't find any favorite tracks in your TIDAL account to use as seeds for recommendations."
            }
        
        # Use these as our seed tracks
        seed_track_ids = [track["id"] for track in favorite_tracks]
        seed_tracks_info = favorite_tracks
    
    # Get recommendations based on the seed tracks
    recommendations_response = _get_tidal_recommendations(
        track_ids=seed_track_ids,
        limit_per_track=limit_per_track,
        filter_criteria=filter_criteria
    )
    
    # Check if we successfully retrieved recommendations
    if "status" in recommendations_response and recommendations_response["status"] == "error":
        return {
            "status": "error",
            "message": f"Unable to get recommendations: {recommendations_response['message']}"
        }
    
    # Get the recommendations
    recommendations = recommendations_response.get("recommendations", [])
    
    if not recommendations:
        return {
            "status": "error",
            "message": "I couldn't find any recommendations based on the provided tracks. Please try again with different tracks or adjust your filtering criteria."
        }
    
    # Return the structured data to process
    return {
        "status": "success",
        "seed_tracks": seed_tracks_info,  # This might be empty if direct track_ids were provided
        "seed_track_ids": seed_track_ids,
        "recommendations": recommendations,
        "filter_criteria": filter_criteria,
        "seed_count": len(seed_track_ids),
    }


@mcp.tool()
def create_tidal_playlist(title: str, track_ids: list, description: str = "") -> dict:
    """
    Creates a new TIDAL playlist with the specified tracks.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Create a playlist with these songs"
    - "Make a TIDAL playlist"
    - "Save these tracks to a playlist"
    - "Create a collection of songs"
    - Any request to create a new playlist in their TIDAL account
    
    This function creates a new playlist in the user's TIDAL account and adds the specified tracks to it.
    The user must be authenticated with TIDAL first.

    NAMING CONVENTION GUIDANCE:
    When suggesting or creating a playlist, first check the user's existing playlists using get_user_playlists()
    to understand their naming preferences. Some patterns to look for:
    - Do they use emoji in playlist names?
    - Do they use all caps, title case, or lowercase?
    - Do they include dates or seasons in names?
    - Do they name by mood, genre, activity, or artist?
    - Do they use specific prefixes or formatting (e.g., "Mix: Summer Vibes" or "[Workout] High Energy")
    
    Try to match their style when suggesting new playlist names. If they have no playlists yet or you 
    can't determine a pattern, use a clear, descriptive name based on the tracks' common themes.
    
    When processing the results of this tool:
    1. Confirm the playlist was created successfully
    2. Provide the playlist title, number of tracks added, and URL
    3. Always include the direct TIDAL URL (https://tidal.com/playlist/{playlist_id})
    4. Suggest that the user can now access this playlist in their TIDAL account
    
    Args:
        title: The name of the playlist to create
        track_ids: List of TIDAL track IDs to add to the playlist
        description: Optional description for the playlist (default: "")
        
    Returns:
        A dictionary containing the status of the playlist creation and details about the created playlist
    """
    try:
        # First, check if the user is authenticated
        auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
        auth_data = auth_check.json()
        
        if not auth_data.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first before creating a playlist. Please use the tidal_login() function."
            }
        
        # Validate inputs
        if not title:
            return {
                "status": "error",
                "message": "Playlist title cannot be empty."
            }
            
        if not track_ids or not isinstance(track_ids, list) or len(track_ids) == 0:
            return {
                "status": "error",
                "message": "You must provide at least one track ID to add to the playlist."
            }
        
        # Create the playlist through the FastAPI API
        payload = {
            "title": title,
            "description": description,
            "track_ids": track_ids
        }
        
        response = requests.post(f"{FASTAPI_APP_URL}/api/playlists", json=payload)
        
        # Check response
        if response.status_code != 200:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to create playlist: {error_data.get('error', 'Unknown error')}"
            }
            
        # Parse the response
        result = response.json()
        playlist_data = result.get("playlist", {})
        
        # Get the playlist ID
        playlist_id = playlist_data.get("id")
        
        # Format the TIDAL URL
        playlist_url = f"https://tidal.com/playlist/{playlist_id}" if playlist_id else None        
        playlist_data["playlist_url"] = playlist_url
        
        return {
            "status": "success",
            "message": f"Successfully created playlist '{title}' with {len(track_ids)} tracks",
            "playlist": playlist_data            
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to create playlist: {str(e)}"
        }
    

@mcp.tool()
def get_user_playlists() -> dict:
    """
    Fetches the user's playlists from their TIDAL account.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Show me my playlists"
    - "List my TIDAL playlists"
    - "What playlists do I have?"
    - "Get my music collections"
    - Any request to view or list their TIDAL playlists
    
    This function retrieves the user's playlists from TIDAL and returns them sorted
    by last updated date (most recent first).
    
    When processing the results of this tool:
    1. Present the playlists in a clear, organized format
    2. Include key information like title, track count, and the TIDAL URL for each playlist
    3. Mention when each playlist was last updated if available
    4. If the user has many playlists, focus on the most recently updated ones unless specified otherwise
    
    Returns:
        A dictionary containing the user's playlists sorted by last updated date
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before I can fetch your playlists. Please use the tidal_login() function."
        }
    
    try:
        # Call the FastAPI endpoint to retrieve playlists with the specified limit
        response = requests.get(f"{FASTAPI_APP_URL}/api/playlists")
        
        # Check if the request was successful
        if response.status_code == 200:
            return {
                "status": "success",
                "playlists": response.json().get("playlists", []),
                "playlist_count": len(response.json().get("playlists", []))
            }
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to retrieve playlists: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL playlists service: {str(e)}"
        }
    

@mcp.tool()
def get_playlist_tracks(playlist_id: str, limit: int = 100) -> dict:
    """
    Retrieves all tracks from a specified TIDAL playlist.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Show me the songs in my playlist"
    - "What tracks are in my [playlist name] playlist?"
    - "List the songs from my playlist"
    - "Get tracks from my playlist"
    - "View contents of my TIDAL playlist"
    - Any request to see what songs/tracks are in a specific playlist
    
    This function retrieves all tracks from a specific playlist in the user's TIDAL account.
    The playlist_id must be provided, which can be obtained from the get_user_playlists() function.
    
    When processing the results of this tool:
    1. Present the playlist information (title, description, track count) as context
    2. List the tracks in a clear, organized format with track name, artist, and album
    3. Include track durations where available
    4. Mention the total number of tracks in the playlist
    5. If there are many tracks, focus on highlighting interesting patterns or variety
    
    Args:
        playlist_id: The TIDAL ID of the playlist to retrieve (required)
        limit: Maximum number of tracks to retrieve (default: 100)
        
    Returns:
        A dictionary containing the playlist information and all tracks in the playlist
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before I can fetch playlist tracks. Please use the tidal_login() function."
        }
    
    # Validate playlist_id
    if not playlist_id:
        return {
            "status": "error", 
            "message": "A playlist ID is required. You can get playlist IDs by using the get_user_playlists() function."
        }
    
    try:
        # Call the FastAPI endpoint to retrieve tracks from the playlist
        response = requests.get(
            f"{FASTAPI_APP_URL}/api/playlists/{playlist_id}/tracks", 
            params={"limit": limit}
        )
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            return {
                "status": "success",                
                "tracks": data.get("tracks", []),
                "track_count": data.get("total_tracks", 0)
            }
        elif response.status_code == 404:
            return {
                "status": "error",
                "message": f"Playlist with ID {playlist_id} not found. Please check the playlist ID and try again."
            }
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to retrieve playlist tracks: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL playlist service: {str(e)}"
        }
    

@mcp.tool()
def delete_tidal_playlist(playlist_id: str) -> dict:
    """
    Deletes a TIDAL playlist by its ID.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Delete my playlist"
    - "Remove a playlist from my TIDAL account"
    - "Get rid of this playlist"
    - "Delete the playlist with ID X"
    - Any request to delete or remove a TIDAL playlist
    
    This function deletes a specific playlist from the user's TIDAL account.
    The user must be authenticated with TIDAL first.
    
    When processing the results of this tool:
    1. Confirm the playlist was deleted successfully
    2. Provide a clear message about the deletion
    
    Args:
        playlist_id: The TIDAL ID of the playlist to delete (required)
        
    Returns:
        A dictionary containing the status of the playlist deletion
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before deleting a playlist. Please use the tidal_login() function."
        }
    
    # Validate playlist_id
    if not playlist_id:
        return {
            "status": "error", 
            "message": "A playlist ID is required. You can get playlist IDs by using the get_user_playlists() function."
        }
    
    try:
        # Call the FastAPI endpoint to delete the playlist
        response = requests.delete(f"{FASTAPI_APP_URL}/api/playlists/{playlist_id}")
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {
                "status": "error",
                "message": f"Playlist with ID {playlist_id} not found. Please check the playlist ID and try again."
            }
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Failed to delete playlist: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL playlist service: {str(e)}"
        }


@mcp.tool()
def search_tidal(query: str, limit: int = 20, search_types: Optional[str] = "tracks,albums,artists") -> dict:
    """
    Search for tracks, albums, and/or artists on TIDAL.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Search for [song/album/artist name]"
    - "Find tracks by [artist]"
    - "Look up [album name]"
    - "Search TIDAL for [anything]"
    - Any request to search or find music on TIDAL
    
    This function searches TIDAL's catalog for tracks, albums, and artists based on a query string.
    
    When processing the results of this tool:
    1. Present search results in a clear, organized format
    2. Group results by type (tracks, albums, artists) with descriptive headings
    3. For tracks: Include track name, artist, album, duration, and TIDAL URL
    4. For albums: Include album name, artist, release date, track count, and TIDAL URL
    5. For artists: Include artist name and TIDAL URL
    6. Always include the TIDAL URL for easy access
    7. If no results are found, suggest alternative search terms
    
    Args:
        query: The search query string (required)
        limit: Maximum number of results per type (default: 20, max: 50)
        search_types: Comma-separated list of types to search. Options: "tracks", "albums", "artists". 
                     Default: "tracks,albums,artists" (searches all types)
                     Examples: "tracks", "albums,artists", "tracks,albums"
    
    Returns:
        A dictionary containing search results for the requested types
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before searching. Please use the tidal_login() function."
        }
    
    # Validate query
    if not query or not query.strip():
        return {
            "status": "error",
            "message": "Search query cannot be empty."
        }
    
    try:
        # Call the FastAPI search endpoint
        response = requests.get(
            f"{FASTAPI_APP_URL}/api/search",
            params={
                "q": query,
                "limit": limit,
                "types": search_types or "tracks,albums,artists"
            }
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Search failed: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL search service: {str(e)}"
        }


@mcp.tool()
def search_tidal_tracks(query: str, limit: int = 20) -> dict:
    """
    Search for tracks on TIDAL.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Search for the song [name]"
    - "Find tracks by [artist]"
    - "Look up the track [name]"
    - Any request to search specifically for tracks/songs
    
    This function searches TIDAL's catalog for tracks based on a query string.
    
    When processing the results of this tool:
    1. Present tracks in a clear list format
    2. For each track, include: track name, artist, album, duration, and TIDAL URL
    3. Always include the TIDAL URL for easy access
    4. If no results are found, suggest alternative search terms
    
    Args:
        query: The search query string (required)
        limit: Maximum number of results (default: 20, max: 50)
    
    Returns:
        A dictionary containing matching tracks
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before searching. Please use the tidal_login() function."
        }
    
    # Validate query
    if not query or not query.strip():
        return {
            "status": "error",
            "message": "Search query cannot be empty."
        }
    
    try:
        # Call the FastAPI search tracks endpoint
        response = requests.get(
            f"{FASTAPI_APP_URL}/api/search/tracks",
            params={"q": query, "limit": limit}
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Track search failed: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL search service: {str(e)}"
        }


@mcp.tool()
def search_tidal_albums(query: str, limit: int = 20) -> dict:
    """
    Search for albums on TIDAL.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Search for the album [name]"
    - "Find albums by [artist]"
    - "Look up the album [name]"
    - Any request to search specifically for albums
    
    This function searches TIDAL's catalog for albums based on a query string.
    
    When processing the results of this tool:
    1. Present albums in a clear list format
    2. For each album, include: album name, artist, release date, track count, and TIDAL URL
    3. Always include the TIDAL URL for easy access
    4. If no results are found, suggest alternative search terms
    
    Args:
        query: The search query string (required)
        limit: Maximum number of results (default: 20, max: 50)
    
    Returns:
        A dictionary containing matching albums
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before searching. Please use the tidal_login() function."
        }
    
    # Validate query
    if not query or not query.strip():
        return {
            "status": "error",
            "message": "Search query cannot be empty."
        }
    
    try:
        # Call the FastAPI search albums endpoint
        response = requests.get(
            f"{FASTAPI_APP_URL}/api/search/albums",
            params={"q": query, "limit": limit}
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Album search failed: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL search service: {str(e)}"
        }


@mcp.tool()
def search_tidal_artists(query: str, limit: int = 20) -> dict:
    """
    Search for artists on TIDAL.
    
    USE THIS TOOL WHENEVER A USER ASKS FOR:
    - "Search for the artist [name]"
    - "Find [artist name]"
    - "Look up the artist [name]"
    - Any request to search specifically for artists
    
    This function searches TIDAL's catalog for artists based on a query string.
    
    When processing the results of this tool:
    1. Present artists in a clear list format
    2. For each artist, include: artist name and TIDAL URL
    3. Always include the TIDAL URL for easy access
    4. If no results are found, suggest alternative search terms
    
    Args:
        query: The search query string (required)
        limit: Maximum number of results (default: 20, max: 50)
    
    Returns:
        A dictionary containing matching artists
    """
    # First, check if the user is authenticated
    auth_check = requests.get(f"{FASTAPI_APP_URL}/api/auth/status")
    auth_data = auth_check.json()
    
    if not auth_data.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first before searching. Please use the tidal_login() function."
        }
    
    # Validate query
    if not query or not query.strip():
        return {
            "status": "error",
            "message": "Search query cannot be empty."
        }
    
    try:
        # Call the FastAPI search artists endpoint
        response = requests.get(
            f"{FASTAPI_APP_URL}/api/search/artists",
            params={"q": query, "limit": limit}
        )
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {
                "status": "error",
                "message": "Not authenticated with TIDAL. Please login first using tidal_login()."
            }
        else:
            error_data = response.json()
            return {
                "status": "error",
                "message": f"Artist search failed: {error_data.get('error', 'Unknown error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to connect to TIDAL search service: {str(e)}"
        }