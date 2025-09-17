from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.config import get_db
from backend.dependencies.get_current_user import get_current_user
from backend.utils.spotify import make_spotify_request

# Create a new router for all stat-related endpoints
stats_router = APIRouter(prefix="/", tags=["stats"])

@stats_router.get("/top/{item_type}")
async def get_top_items(
    # This defines a path parameter that must be either "artists" or "tracks"
    item_type: str,
    # This defines optional query parameters with default values and validation
    time_range: str = Query("medium_term", enum=["short_term", "medium_term", "long_term"]),
    limit: int = Query(20, ge=1, le=50),
    # These two lines secure the endpoint and provide a database session
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetches the user's top items (artists or tracks) from the Spotify API
    using our centralized, token-refreshing helper function.
    """
    # 1. Basic validation to ensure the item_type is correct
    if item_type not in ["artists", "tracks"]:
        raise HTTPException(status_code=400, detail="Invalid item type. Must be 'artists' or 'tracks'.")

    # 2. Get the user's ID from the validated JWT payload
    user_id = user.get('id')
    
    # 3. Prepare the specific Spotify endpoint and parameters for the request
    endpoint = f"/me/top/{item_type}"
    params = {"time_range": time_range, "limit": limit}
    
    # 4. Call our powerful helper function.
    #    All the complexity of token refreshing and making the actual API call
    #    is handled by this one, clean line of code.
    spotify_data = make_spotify_request(user_id, db, endpoint, params=params)
    
    # 5. Return the data received from Spotify directly to the frontend.
    return spotify_data

@stats_router.get("/recently-played")
async def get_recently_played(
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's recently played tracks from Spotify.
    
    Args:
        limit: Number of tracks to return (max 50)
        user: Current authenticated user
        db: Database session
    
    Returns:
        User's recently played tracks data from Spotify API
    """
    user_id = user.get('id')
    
    params = {
        "limit": limit
    }
    
    try:
        data = make_spotify_request(
            user_id=user_id,
            db=db,
            endpoint="/me/player/recently-played",
            params=params
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recently played tracks: {str(e)}")

@stats_router.get("/profile")
async def get_user_profile(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's Spotify profile information.
    
    Args:
        user: Current authenticated user
        db: Database session
    
    Returns:
        User's Spotify profile data
    """
    user_id = user.get('id')
    
    try:
        data = make_spotify_request(
            user_id=user_id,
            db=db,
            endpoint="/me"
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching user profile: {str(e)}")

@stats_router.get("/audio-features/{track_id}")
async def get_audio_features(
    track_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get audio features for a specific track.
    
    Args:
        track_id: Spotify track ID
        user: Current authenticated user
        db: Database session
    
    Returns:
        Audio features data for the specified track
    """
    user_id = user.get('id')
    
    try:
        data = make_spotify_request(
            user_id=user_id,
            db=db,
            endpoint=f"/audio-features/{track_id}"
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audio features: {str(e)}")