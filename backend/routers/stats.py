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

# --- NEW ENDPOINT FOR VIBE ANALYSIS ---

@stats_router.get("/vibe")
async def get_vibe_analysis(
    time_range: str = Query("medium_term", enum=["short_term", "medium_term", "long_term"]),
    limit: int = Query(50, ge=1, le=50), # We use up to 50 tracks for a good sample size
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyzes the audio features of a user's top tracks to determine their
    current listening "vibe".
    """
    user_id = user.get('user_id')

    # 1. First, get the user's top tracks using our helper function.
    top_tracks_endpoint = "/me/top/tracks"
    top_tracks_params = {"time_range": time_range, "limit": limit}
    top_tracks_data = await make_spotify_request(user_id, db, top_tracks_endpoint, params=top_tracks_params)

    # 2. Extract the IDs of all the tracks from the response.
    track_ids = [track['id'] for track in top_tracks_data.get('items', []) if track.get('id')]
    if not track_ids:
        # Handle cases where the user has no listening history for the time range.
        return {"message": "No top tracks found to analyze for this period."}

    # 3. Next, get the audio features for all of those tracks in a single API call.
    audio_features_endpoint = "/audio-features"
    audio_features_params = {"ids": ",".join(track_ids)}
    audio_features_data = await make_spotify_request(user_id, db, audio_features_endpoint, params=audio_features_params)

    features_list = audio_features_data.get('audio_features', [])
    # Filter out any potential null entries from the response
    features_list = [f for f in features_list if f]
    if not features_list:
        raise HTTPException(status_code=404, detail="Could not retrieve audio features for the tracks.")

    # 4. Calculate the average for each "vibe" metric.
    total_tracks = len(features_list)
    avg_danceability = sum(f['danceability'] for f in features_list) / total_tracks
    avg_energy = sum(f['energy'] for f in features_list) / total_tracks
    avg_valence = sum(f['valence'] for f in features_list) / total_tracks  # Fixed: added division
    avg_acousticness = sum(f['acousticness'] for f in features_list) / total_tracks
    
    # 5. Return the calculated vibe as a simple, clean JSON object.
    return {
        "time_range": time_range,
        "tracks_analyzed": total_tracks,
        "danceability": round(avg_danceability * 100), # Return as a percentage
        "energy": round(avg_energy * 100),
        "positivity": round(avg_valence * 100), # Renamed for clarity
        "acousticness": round(avg_acousticness * 100),
    }