"""
Pydantic models for TIDAL MCP API.

This module defines all data models used for request/response validation
and serialization throughout the API.
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, field_validator


# ============================================================================
# Core Data Models
# ============================================================================

class TrackModel(BaseModel):
    """Model representing a TIDAL track."""
    id: Optional[str] = Field(None, description="TIDAL track ID")
    title: str = Field(..., description="Track title")
    artist: str = Field(..., description="Artist name")
    album: str = Field(..., description="Album name")
    duration: int = Field(0, ge=0, description="Track duration in seconds")
    url: Optional[HttpUrl] = Field(None, description="TIDAL track URL")
    source_track_id: Optional[str] = Field(None, description="Source track ID for recommendations")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "12345678",
                "title": "Bohemian Rhapsody",
                "artist": "Queen",
                "album": "A Night at the Opera",
                "duration": 355,
                "url": "https://tidal.com/browse/track/12345678?u"
            }
        }


class AlbumModel(BaseModel):
    """Model representing a TIDAL album."""
    id: Optional[str] = Field(None, description="TIDAL album ID")
    title: str = Field(..., description="Album title")
    artist: str = Field(..., description="Artist name")
    release_date: Optional[str] = Field(None, description="Album release date")
    duration: int = Field(0, ge=0, description="Total album duration in seconds")
    num_tracks: int = Field(0, ge=0, description="Number of tracks in album")
    url: Optional[HttpUrl] = Field(None, description="TIDAL album URL")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "87654321",
                "title": "A Night at the Opera",
                "artist": "Queen",
                "release_date": "1975-10-31",
                "duration": 4320,
                "num_tracks": 12,
                "url": "https://tidal.com/browse/album/87654321?u"
            }
        }


class ArtistModel(BaseModel):
    """Model representing a TIDAL artist."""
    id: Optional[str] = Field(None, description="TIDAL artist ID")
    name: str = Field(..., description="Artist name")
    url: Optional[HttpUrl] = Field(None, description="TIDAL artist URL")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "11111111",
                "name": "Queen",
                "url": "https://tidal.com/browse/artist/11111111?u"
            }
        }


class UserModel(BaseModel):
    """Model representing a TIDAL user."""
    id: str = Field(..., description="User ID")
    username: Optional[str] = Field("N/A", description="Username")
    email: Optional[str] = Field("N/A", description="User email")


class PlaylistModel(BaseModel):
    """Model representing a TIDAL playlist."""
    id: str = Field(..., description="Playlist ID")
    title: str = Field(..., description="Playlist title")
    description: str = Field("", description="Playlist description")
    created: Optional[datetime] = Field(None, description="Creation timestamp")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")
    track_count: int = Field(0, ge=0, description="Number of tracks")
    duration: int = Field(0, ge=0, description="Total duration in seconds")
    url: Optional[HttpUrl] = Field(None, description="TIDAL playlist URL")


# ============================================================================
# Request Models
# ============================================================================

class BatchRecommendationsRequest(BaseModel):
    """Request model for batch track recommendations."""
    track_ids: List[str] = Field(..., min_length=1, description="List of TIDAL track IDs")
    limit_per_track: int = Field(20, ge=1, le=50, description="Maximum recommendations per track")
    remove_duplicates: bool = Field(True, description="Remove duplicate tracks across recommendations")

    @field_validator('track_ids')
    @classmethod
    def validate_track_ids(cls, v: List[str]) -> List[str]:
        """Ensure track_ids list is not empty."""
        if not v:
            raise ValueError("track_ids cannot be empty")
        return v


class CreatePlaylistRequest(BaseModel):
    """Request model for creating a playlist."""
    title: str = Field(..., min_length=1, max_length=200, description="Playlist title")
    description: str = Field("", max_length=1000, description="Playlist description")
    track_ids: List[str] = Field(..., min_length=1, description="List of TIDAL track IDs to add")

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Ensure title is not empty."""
        if not v.strip():
            raise ValueError("title cannot be empty or whitespace only")
        return v.strip()


# ============================================================================
# Response Models
# ============================================================================

class LoginResponse(BaseModel):
    """Response model for login endpoint."""
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Status message")
    user_id: Optional[str] = Field(None, description="User ID if successful")


class AuthStatusResponse(BaseModel):
    """Response model for authentication status endpoint."""
    authenticated: bool = Field(..., description="Whether user is authenticated")
    message: str = Field(..., description="Status message")
    user: Optional[UserModel] = Field(None, description="User information if authenticated")


class TracksResponse(BaseModel):
    """Response model for tracks endpoint."""
    tracks: List[TrackModel] = Field(..., description="List of tracks")


class RecommendationsResponse(BaseModel):
    """Response model for recommendations endpoint."""
    recommendations: List[TrackModel] = Field(..., description="List of recommended tracks")


class BatchRecommendationsResponse(BaseModel):
    """Response model for batch recommendations endpoint."""
    recommendations: List[TrackModel] = Field(..., description="List of recommended tracks")


class CreatePlaylistResponse(BaseModel):
    """Response model for playlist creation endpoint."""
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Status message")
    playlist: PlaylistModel = Field(..., description="Created playlist information")


class PlaylistsResponse(BaseModel):
    """Response model for playlists list endpoint."""
    playlists: List[PlaylistModel] = Field(..., description="List of playlists")


class PlaylistTracksResponse(BaseModel):
    """Response model for playlist tracks endpoint."""
    playlist_id: str = Field(..., description="Playlist ID")
    tracks: List[TrackModel] = Field(..., description="List of tracks in playlist")
    total_tracks: int = Field(..., ge=0, description="Total number of tracks")


class DeletePlaylistResponse(BaseModel):
    """Response model for playlist deletion endpoint."""
    status: str = Field(..., description="Status of the operation")
    message: str = Field(..., description="Status message")


class SearchResultsModel(BaseModel):
    """Model for search results containing multiple types."""
    tracks: List[TrackModel] = Field(default_factory=list, description="Matching tracks")
    albums: List[AlbumModel] = Field(default_factory=list, description="Matching albums")
    artists: List[ArtistModel] = Field(default_factory=list, description="Matching artists")


class SearchResponse(BaseModel):
    """Response model for general search endpoint."""
    query: str = Field(..., description="Search query")
    results: SearchResultsModel = Field(..., description="Search results")
    total_tracks: int = Field(0, ge=0, description="Total number of track results")
    total_albums: int = Field(0, ge=0, description="Total number of album results")
    total_artists: int = Field(0, ge=0, description="Total number of artist results")


class SearchTracksResponse(BaseModel):
    """Response model for track search endpoint."""
    query: str = Field(..., description="Search query")
    tracks: List[TrackModel] = Field(..., description="Matching tracks")
    total: int = Field(..., ge=0, description="Total number of results")


class SearchAlbumsResponse(BaseModel):
    """Response model for album search endpoint."""
    query: str = Field(..., description="Search query")
    albums: List[AlbumModel] = Field(..., description="Matching albums")
    total: int = Field(..., ge=0, description="Total number of results")


class SearchArtistsResponse(BaseModel):
    """Response model for artist search endpoint."""
    query: str = Field(..., description="Search query")
    artists: List[ArtistModel] = Field(..., description="Matching artists")
    total: int = Field(..., ge=0, description="Total number of results")

