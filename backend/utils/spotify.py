import requests
import os
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import UserToken

# It's best practice to get these from environment variables
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

async def _refresh_spotify_token(user_id: str, db: AsyncSession) -> UserToken:
    """
    Refreshes the Spotify access token if it's expired and updates the database.
    This is a private helper function.
    """
    print(f"Looking for token for user_id: {user_id}")
    
    # Use async query syntax
    result = await db.execute(select(UserToken).filter(UserToken.id == user_id))
    token_record = result.scalar_one_or_none()
    
    if not token_record:
        print(f"No token found for user {user_id}")
        raise HTTPException(status_code=404, detail="Spotify token not found for user.")

    print(f"Token found. Expires at: {token_record.expires_at}")
    
    # Check if the token is within 5 minutes of expiring for safety
    # We use timezone.utc to make the comparison timezone-aware
    current_time = datetime.now(timezone.utc)
    expires_at = token_record.expires_at
    
    # Make sure expires_at is timezone-aware
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if current_time >= expires_at - timedelta(minutes=5):
        print(f"Spotify token for user {user_id} is expiring. Refreshing...")
        
        if not token_record.refresh_token:
            print(f"No refresh token available for user {user_id}")
            raise HTTPException(status_code=400, detail="No refresh token available.")
        
        refresh_data = {
            'grant_type': 'refresh_token',
            'refresh_token': token_record.refresh_token,
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET,
        }
        
        print(f"Attempting to refresh token with client_id: {SPOTIFY_CLIENT_ID}")
        response = requests.post('https://accounts.spotify.com/api/token', data=refresh_data)
        
        if response.status_code != 200:
            print(f"Error refreshing token: {response.text}")
            raise HTTPException(status_code=response.status_code, detail=f"Failed to refresh Spotify token: {response.text}")
            
        new_token_data = response.json()
        
        # Update the token record in the database
        token_record.access_token = new_token_data['access_token']
        # Ensure the new expiry time is timezone-aware (UTC)
        token_record.expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_token_data['expires_in'])
        
        # Commit changes with async session
        await db.commit()
        await db.refresh(token_record)
        print("Token refreshed and updated in DB.")
    else:
        print("Token is still valid, no refresh needed.")

    return token_record

async def make_spotify_request(user_id: str, db: AsyncSession, endpoint: str, method: str = "GET", params: dict = None, data: dict = None):
    """
    A centralized helper to make authenticated requests to the Spotify API.
    It automatically handles token refreshing.
    """
    print(f"Making Spotify request to {endpoint} for user {user_id}")
    
    # Check if we have environment variables
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print(f"Missing Spotify credentials: CLIENT_ID={SPOTIFY_CLIENT_ID}, CLIENT_SECRET={'***' if SPOTIFY_CLIENT_SECRET else None}")
        raise HTTPException(status_code=500, detail="Spotify API credentials not configured")
    
    # 1. Get a fresh token
    token_record = await _refresh_spotify_token(user_id, db)
    
    # 2. Prepare the request
    headers = {"Authorization": f"Bearer {token_record.access_token}"}
    url = f"{SPOTIFY_API_BASE_URL}{endpoint}"
    
    print(f"Making request to: {url}")
    print(f"With headers: Authorization: Bearer {token_record.access_token[:20]}...")
    
    # 3. Make the API call
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise HTTPException(status_code=405, detail=f"Method {method} not allowed.")

        print(f"Response status: {response.status_code}")
        
        if response.status_code == 401:
            print("Received 401 Unauthorized - token might be invalid")
            print(f"Response body: {response.text}")
            raise HTTPException(status_code=401, detail="Invalid token")
        
        response.raise_for_status()  # Raises an exception for bad responses (4xx or 5xx)
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"Request exception: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error response JSON: {error_detail}")
            except:
                error_detail = e.response.text
                print(f"Error response text: {error_detail}")
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        else:
            print(f"No response object in exception: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))