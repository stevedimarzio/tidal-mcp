from fastmcp import FastMCP
from starlette.responses import JSONResponse
from starlette.requests import Request
import uuid
import os

from mcp_server.logger import logger
from mcp_server.wireup_config import container

mcp = FastMCP("TIDAL MCP")
logger.info("TIDAL MCP server initialized")


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    """Health check endpoint for monitoring and load balancers."""
    return JSONResponse({"status": "healthy", "service": "tidal-mcp"})


@mcp.custom_route("/auth/login", methods=["POST"])
async def http_login(request: Request):
    """
    HTTP endpoint to start TIDAL authentication.
    Returns auth URL immediately for cloud deployment.
    Sets a session cookie for tracking.
    
    Accepts optional 'callback_url' in JSON body for redirect after login.
    """
    try:
        # Get callback URL from request body if provided
        callback_url = None
        try:
            body = await request.json()
            callback_url = body.get("callback_url")
        except Exception:
            pass
        
        # Get or create session ID from cookie
        session_id = request.cookies.get("tidal_session_id")
        if not session_id:
            session_id = str(uuid.uuid4())
        
        result = container.session_manager.authenticate(
            session_id=session_id,
            callback_url=callback_url
        )
        
        # Set session ID in service
        if "session_id" in result:
            container.tidal_service.set_session_id(result["session_id"])
        
        response = JSONResponse(result)
        # Set session cookie (30 days expiry)
        # Cookie security: use HTTPS in production
        is_https = os.getenv("HTTPS_ENABLED", "false").lower() == "true"
        response.set_cookie(
            key="tidal_session_id",
            value=result.get("session_id", session_id),
            max_age=30 * 24 * 60 * 60,  # 30 days
            httponly=True,
            samesite="lax",
            secure=is_https,  # Set HTTPS_ENABLED=true in production
        )
        return response
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": f"Authentication failed: {str(e)}"},
            status_code=500
        )


@mcp.custom_route("/auth/status", methods=["GET"])
async def http_status_check(request: Request):
    """
    HTTP endpoint to check authentication status.
    Uses session ID from cookie or query parameter.
    Returns callback_url if authentication completed and callback was set.
    """
    try:
        # Get session ID from cookie or query parameter
        session_id = request.cookies.get("tidal_session_id") or request.query_params.get("session_id")
        
        if not session_id:
            return JSONResponse(
                {"status": "error", "message": "No session ID provided"},
                status_code=400
            )
        
        result = container.session_manager.check_login_status(session_id)
        
        # Set session ID in service if authenticated
        if result.get("authenticated"):
            container.tidal_service.set_session_id(session_id)
        
        return JSONResponse(result)
    except Exception as e:
        logger.error(f"Status check error: {e}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": f"Status check failed: {str(e)}"},
            status_code=500
        )


@mcp.custom_route("/auth/callback", methods=["GET"])
async def auth_callback(request: Request):
    """
    Callback endpoint for redirect after authentication.
    Redirects to the callback URL if authentication is complete.
    """
    from starlette.responses import RedirectResponse
    
    try:
        session_id = request.query_params.get("session_id")
        if not session_id:
            return JSONResponse(
                {"status": "error", "message": "No session ID provided"},
                status_code=400
            )
        
        # Check authentication status
        result = container.session_manager.check_login_status(session_id)
        
        if result.get("authenticated"):
            callback_url = result.get("callback_url")
            if callback_url:
                # Redirect to callback URL
                logger.info(f"Redirecting session {session_id} to callback URL")
                return RedirectResponse(url=callback_url, status_code=302)
            else:
                return JSONResponse({
                    "status": "success",
                    "message": "Authentication successful",
                    "session_id": session_id,
                })
        else:
            return JSONResponse({
                "status": result.get("status", "pending"),
                "message": result.get("message", "Authentication not yet complete"),
                "session_id": session_id,
            }, status_code=202)  # Accepted but not complete
    except Exception as e:
        logger.error(f"Callback error: {e}", exc_info=True)
        return JSONResponse(
            {"status": "error", "message": f"Callback failed: {str(e)}"},
            status_code=500
        )


@mcp.tool()
def tidal_login(session_id: str | None = None, callback_url: str | None = None) -> dict:
    """
    Authenticate with TIDAL through browser login flow.
    Returns the authentication URL immediately for cloud deployment compatibility.
    Use check_login_status() to check if authentication completed.

    Args:
        session_id: Optional session ID. If not provided, a new one will be generated.
        callback_url: Optional callback URL for automatic redirect after login.
                     The user will be redirected to this URL once authentication completes.
                     Use this to redirect back to the chat interface.

    Returns:
        Dictionary containing:
        - status: "pending" (needs user action) or "success" (already authenticated)
        - auth_url: URL to visit for authentication (if status is "pending")
        - session_id: Session ID to use for checking status and subsequent requests
        - expires_in: Seconds until the auth code expires
        - callback_url: Echo of the callback URL if provided
    """
    try:
        result = container.session_manager.authenticate(
            session_id=session_id,
            callback_url=callback_url
        )
        # Set session ID in service for subsequent calls
        if "session_id" in result:
            container.tidal_service.set_session_id(result["session_id"])
        return result
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        return {"status": "error", "message": f"Authentication failed: {str(e)}"}


@mcp.tool()
def check_login_status(session_id: str) -> dict:
    """
    Check the status of a TIDAL authentication flow.

    Use this after calling tidal_login() to check if the user has completed authentication.

    Args:
        session_id: The session ID returned from tidal_login()

    Returns:
        Dictionary containing authentication status and user information if authenticated
    """
    try:
        return container.session_manager.check_login_status(session_id)
    except Exception as e:
        logger.error(f"Status check error: {e}", exc_info=True)
        return {"status": "error", "message": f"Status check failed: {str(e)}"}


@mcp.tool()
def get_favorite_tracks(limit: int = 20, session_id: str | None = None) -> dict:
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
        session_id: Optional session ID. If not provided, uses the default session.

    Returns:
        A dictionary containing track information including track ID, title, artist, album, and duration.
        Returns an error message if not authenticated or if retrieval fails.
    """
    try:
        # Set session ID if provided
        if session_id:
            container.tidal_service.set_session_id(session_id)
        
        auth_status = container.session_manager.check_authentication_status(session_id)
        if not auth_status.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
            }

        response = container.tidal_service.get_favorite_tracks(limit=limit)
        return {"tracks": [track.model_dump() for track in response.tracks]}
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error getting favorite tracks: {e}", exc_info=True)
        return {"status": "error", "message": f"Failed to retrieve tracks: {str(e)}"}


def _get_session_id_for_tool(session_id: str | None = None) -> str | None:
    """Helper to set session ID in service if provided."""
    if session_id:
        container.tidal_service.set_session_id(session_id)
    return session_id


def _get_tidal_recommendations(
    track_ids: list = None, limit_per_track: int = 20, filter_criteria: str = None, session_id: str | None = None
) -> dict:
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
        _get_session_id_for_tool(session_id)
        
        if not track_ids or not isinstance(track_ids, list) or len(track_ids) == 0:
            return {"status": "error", "message": "No track IDs provided for recommendations."}

        response = container.tidal_service.get_batch_recommendations(
            track_ids=track_ids, limit_per_track=limit_per_track, remove_duplicates=True
        )

        recommendations = [track.model_dump() for track in response.recommendations]
        result = {"recommendations": recommendations, "total_count": len(recommendations)}

        if filter_criteria:
            result["filter_criteria"] = filter_criteria

        return result

    except Exception as e:
        logger.error(f"Error getting recommendations: {e}", exc_info=True)
        return {"status": "error", "message": f"Failed to get recommendations: {str(e)}"}


@mcp.tool()
def recommend_tracks(
    track_ids: list[str] | None = None,
    filter_criteria: str | None = None,
    limit_per_track: int = 20,
    limit_from_favorite: int = 20,
    session_id: str | None = None,
) -> dict:
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
    _get_session_id_for_tool(session_id)
    auth_status = container.session_manager.check_authentication_status(session_id)
    if not auth_status.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
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
        try:
            tracks_response = container.tidal_service.get_favorite_tracks(limit=limit_from_favorite)
            favorite_tracks = [track.model_dump() for track in tracks_response.tracks]
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unable to get favorite tracks for recommendations: {str(e)}",
            }

        if not favorite_tracks:
            return {
                "status": "error",
                "message": "I couldn't find any favorite tracks in your TIDAL account to use as seeds for recommendations.",
            }

        # Use these as our seed tracks
        seed_track_ids = [track["id"] for track in favorite_tracks]
        seed_tracks_info = favorite_tracks

    # Get recommendations based on the seed tracks
        recommendations_response = _get_tidal_recommendations(
            track_ids=seed_track_ids, limit_per_track=limit_per_track, filter_criteria=filter_criteria, session_id=session_id
        )

    # Check if we successfully retrieved recommendations
    if "status" in recommendations_response and recommendations_response["status"] == "error":
        return {
            "status": "error",
            "message": f"Unable to get recommendations: {recommendations_response['message']}",
        }

    # Get the recommendations
    recommendations = recommendations_response.get("recommendations", [])

    if not recommendations:
        return {
            "status": "error",
            "message": "I couldn't find any recommendations based on the provided tracks. Please try again with different tracks or adjust your filtering criteria.",
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
def create_tidal_playlist(title: str, track_ids: list, description: str = "", session_id: str | None = None) -> dict:
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
        _get_session_id_for_tool(session_id)
        auth_status = container.session_manager.check_authentication_status(session_id)
        if not auth_status.get("authenticated", False):
            return {
                "status": "error",
                "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
            }

        if not title:
            return {"status": "error", "message": "Playlist title cannot be empty."}

        if not track_ids or not isinstance(track_ids, list) or len(track_ids) == 0:
            return {
                "status": "error",
                "message": "You must provide at least one track ID to add to the playlist.",
            }

        response = container.tidal_service.create_playlist(
            title=title, track_ids=track_ids, description=description
        )
        return {
            "status": response.status,
            "message": response.message,
            "playlist": response.playlist.model_dump(),
        }

    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error creating playlist: {e}", exc_info=True)
        return {"status": "error", "message": f"Failed to create playlist: {str(e)}"}


@mcp.tool()
def get_user_playlists(session_id: str | None = None) -> dict:
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
    _get_session_id_for_tool(session_id)
    auth_status = container.session_manager.check_authentication_status(session_id)
    if not auth_status.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
        }

    try:
        response = container.tidal_service.get_user_playlists()
        return {
            "status": "success",
            "playlists": [playlist.model_dump() for playlist in response.playlists],
            "playlist_count": len(response.playlists),
        }
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error getting playlists: {e}", exc_info=True)
        return {"status": "error", "message": f"Failed to retrieve playlists: {str(e)}"}


@mcp.tool()
def get_playlist_tracks(playlist_id: str, limit: int = 100, session_id: str | None = None) -> dict:
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
    _get_session_id_for_tool(session_id)
    auth_status = container.session_manager.check_authentication_status(session_id)
    if not auth_status.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
        }

    # Validate playlist_id
    if not playlist_id:
        return {
            "status": "error",
            "message": "A playlist ID is required. You can get playlist IDs by using the get_user_playlists() function.",
        }

    try:
        response = container.tidal_service.get_playlist_tracks(playlist_id=playlist_id, limit=limit)
        return {
            "status": "success",
            "tracks": [track.model_dump() for track in response.tracks],
            "track_count": response.total_tracks,
        }
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error getting playlist tracks: {e}", exc_info=True)
        return {"status": "error", "message": f"Failed to retrieve playlist tracks: {str(e)}"}


@mcp.tool()
def delete_tidal_playlist(playlist_id: str, session_id: str | None = None) -> dict:
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
    _get_session_id_for_tool(session_id)
    auth_status = container.session_manager.check_authentication_status(session_id)
    if not auth_status.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
        }

    # Validate playlist_id
    if not playlist_id:
        return {
            "status": "error",
            "message": "A playlist ID is required. You can get playlist IDs by using the get_user_playlists() function.",
        }

    try:
        response = container.tidal_service.delete_playlist(playlist_id=playlist_id)
        return {"status": response.status, "message": response.message}
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error deleting playlist: {e}", exc_info=True)
        return {"status": "error", "message": f"Failed to delete playlist: {str(e)}"}


@mcp.tool()
def search_tidal(
    query: str, limit: int = 20, search_types: str | None = "tracks,albums,artists", session_id: str | None = None
) -> dict:
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
    _get_session_id_for_tool(session_id)
    auth_status = container.session_manager.check_authentication_status(session_id)
    if not auth_status.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
        }

    # Validate query
    if not query or not query.strip():
        return {"status": "error", "message": "Search query cannot be empty."}

    try:
        response = container.tidal_service.search_tidal(
            query=query, limit=limit, search_types=search_types or "tracks,albums,artists"
        )
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
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error searching TIDAL: {e}", exc_info=True)
        return {"status": "error", "message": f"Search failed: {str(e)}"}


@mcp.tool()
def search_tidal_tracks(query: str, limit: int = 20, session_id: str | None = None) -> dict:
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
    _get_session_id_for_tool(session_id)
    auth_status = container.session_manager.check_authentication_status(session_id)
    if not auth_status.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
        }

    # Validate query
    if not query or not query.strip():
        return {"status": "error", "message": "Search query cannot be empty."}

    try:
        response = container.tidal_service.search_tracks(query=query, limit=limit)
        return {
            "query": response.query,
            "tracks": [track.model_dump() for track in response.tracks],
            "total": response.total,
        }
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error searching tracks: {e}", exc_info=True)
        return {"status": "error", "message": f"Track search failed: {str(e)}"}


@mcp.tool()
def search_tidal_albums(query: str, limit: int = 20, session_id: str | None = None) -> dict:
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
    _get_session_id_for_tool(session_id)
    auth_status = container.session_manager.check_authentication_status(session_id)
    if not auth_status.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
        }

    # Validate query
    if not query or not query.strip():
        return {"status": "error", "message": "Search query cannot be empty."}

    try:
        response = container.tidal_service.search_albums(query=query, limit=limit)
        return {
            "query": response.query,
            "albums": [album.model_dump() for album in response.albums],
            "total": response.total,
        }
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error searching albums: {e}", exc_info=True)
        return {"status": "error", "message": f"Album search failed: {str(e)}"}


@mcp.tool()
def search_tidal_artists(query: str, limit: int = 20, session_id: str | None = None) -> dict:
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
    _get_session_id_for_tool(session_id)
    auth_status = container.session_manager.check_authentication_status(session_id)
    if not auth_status.get("authenticated", False):
        return {
            "status": "error",
            "message": "You need to login to TIDAL first. Please use the tidal_login() function.",
        }

    # Validate query
    if not query or not query.strip():
        return {"status": "error", "message": "Search query cannot be empty."}

    try:
        response = container.tidal_service.search_artists(query=query, limit=limit)
        return {
            "query": response.query,
            "artists": [artist.model_dump() for artist in response.artists],
            "total": response.total,
        }
    except RuntimeError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error searching artists: {e}", exc_info=True)
        return {"status": "error", "message": f"Artist search failed: {str(e)}"}


# Server can be run using: fastmcp run mcp_server/server.py --host 0.0.0.0 --port 8080
# FastMCP CLI automatically detects the 'mcp' object and runs it
