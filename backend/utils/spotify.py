import requests
import os
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy.orm import Session
from backend.models import UserToken

# It's best practice to get these from environment variables
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_API_BASE_URL = "https://api.spotify.com/v1"

def _refresh_spotify_token(user_id: str, db: Session) -> UserToken:
    """
    Refreshes the Spotify access token if it's expired and updates the database.
    This is a private helper function.
    """
    token_record = db.query(UserToken).filter(UserToken.id == user_id).first()
    if not token_record:
        raise HTTPException(status_code=404, detail="Spotify token not found for user.")

    # Check if the token is within 5 minutes of expiring for safety
    # We use timezone.utc to make the comparison timezone-aware
    if datetime.now(timezone.utc) >= token_record.expires_at - timedelta(minutes=5):
        print(f"Spotify token for user {user_id} is expiring. Refreshing...")
        
        refresh_data = {
            'grant_type': 'refresh_token',
            'refresh_token': token_record.refresh_token,
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET,
        }
        
        response = requests.post('https://accounts.spotify.com/api/token', data=refresh_data)
        
        if response.status_code != 200:
            print(f"Error refreshing token: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to refresh Spotify token.")
            
        new_token_data = response.json()
        
        # Update the token record in the database
        token_record.access_token = new_token_data['access_token']
        # Ensure the new expiry time is timezone-aware (UTC)
        token_record.expires_at = datetime.now(timezone.utc) + timedelta(seconds=new_token_data['expires_in'])
        db.commit()
        db.refresh(token_record)
        print("Token refreshed and updated in DB.")

    return token_record

def make_spotify_request(user_id: str, db: Session, endpoint: str, method: str = "GET", params: dict = None, data: dict = None):
    """
    A centralized helper to make authenticated requests to the Spotify API.
    It automatically handles token refreshing.
    """
    # 1. Get a fresh token
    token_record = _refresh_spotify_token(user_id, db)
    
    # 2. Prepare the request
    headers = {"Authorization": f"Bearer {token_record.access_token}"}
    url = f"{SPOTIFY_API_BASE_URL}{endpoint}"
    
    # 3. Make the API call
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data)
        else:
            raise HTTPException(status_code=405, detail=f"Method {method} not allowed.")

        response.raise_for_status()  # Raises an exception for bad responses (4xx or 5xx)
        return response.json()
        
    except requests.exceptions.RequestException as e:
        error_detail = e.response.json() if e.response else str(e)
        raise HTTPException(status_code=e.response.status_code if e.response else 500, detail=error_detail)