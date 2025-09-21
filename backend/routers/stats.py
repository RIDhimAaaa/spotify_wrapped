from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from config import get_db
from dependencies.get_current_user import get_current_user
from utils.spotify import make_spotify_request

# Create a new router for all stat-related endpoints
stats_router = APIRouter(prefix="/api/stats", tags=["stats"])

@stats_router.get("/top/{item_type}")
async def get_top_items(
    item_type: str,
    time_range: str = Query("medium_term", enum=["short_term", "medium_term", "long_term"]),
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches the user's top items and transforms the data into a simple,
    clean format for the frontend.
    """
    if item_type not in ["artists", "tracks"]:
        raise HTTPException(status_code=400, detail="Invalid item type. Must be 'artists' or 'tracks'.")

    user_id = user.get('user_id')  # Note: using 'user_id' as per our auth implementation
    
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID not found in token")
    
    endpoint = f"/me/top/{item_type}"
    params = {"time_range": time_range, "limit": limit}
    
    # 1. Get the full, messy data from Spotify
    spotify_data = await make_spotify_request(user_id, db, endpoint, params=params)
    
    # 2. --- NEW: Transform the data ---
    # Create an empty list to hold our clean data
    cleaned_items = []
    
    # Loop through each item in the response from Spotify
    for item in spotify_data.get('items', []):
        if item_type == 'tracks':
            # If it's a track, pull out only what we need
            cleaned_item = {
                "id": item.get('id'),
                "name": item.get('name'),
                # Get the names of all artists and join them with ", "
                "artists": ", ".join([artist['name'] for artist in item.get('artists', [])]),
                # Get the URL of the first (largest) album image
                "image_url": item.get('album', {}).get('images', [{}])[0].get('url')
            }
            cleaned_items.append(cleaned_item)
            
        elif item_type == 'artists':
            # If it's an artist, pull out only what we need
            cleaned_item = {
                "id": item.get('id'),
                "name": item.get('name'),
                # Get the URL of the first (largest) artist image
                "image_url": item.get('images', [{}])[0].get('url'),
                "genres": item.get('genres', [])
            }
            cleaned_items.append(cleaned_item)
            
    # 3. Return the clean list instead of the raw data
    return cleaned_items

@stats_router.get("/recently-played")
async def get_recently_played(
    limit: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
    user_id = user.get('user_id')
    
    params = {
        "limit": limit
    }
    
    try:
        data = await make_spotify_request(
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
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's Spotify profile information.
    
    Args:
        user: Current authenticated user
        db: Database session
    
    Returns:
        User's Spotify profile data
    """
    user_id = user.get('user_id')
    
    try:
        data = await make_spotify_request(
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
    db: AsyncSession = Depends(get_db)
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
    user_id = user.get('user_id')
    
    try:
        data = await make_spotify_request(
            user_id=user_id,
            db=db,
            endpoint=f"/audio-features/{track_id}"
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching audio features: {str(e)}")