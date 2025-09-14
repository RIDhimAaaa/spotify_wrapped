from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession  # Use AsyncSession
from sqlalchemy.dialects.postgresql import insert
from datetime import datetime, timedelta

from config import get_db, supabase
from models import UserToken

# Pydantic model for the incoming request body
class SpotifyTokenPayload(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int

# Dependency to get the current user from the Supabase JWT
async def get_current_user(authorization: str = Header(..., alias="Authorization")):
    """
    Validates the Supabase JWT from the Authorization header and returns the user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization scheme")
    
    jwt = authorization.split("Bearer ")[1]
    try:
        # Use the sync client to get the user
        user_response = supabase.auth.get_user(jwt)
        if user_response.user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user_response.user
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

token_router = APIRouter(prefix="/api/tokens", tags=["tokens"])

@token_router.post("/spotify")
async def store_spotify_tokens(
    payload: SpotifyTokenPayload,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)  # Use AsyncSession
):
    """
    Receives Spotify tokens from the frontend, validates the user's session,
    and securely saves or updates the tokens in the database.
    """
    user_id = user.id
    expires_at = datetime.utcnow() + timedelta(seconds=payload.expires_in)

    stmt = insert(UserToken).values(
        id=user_id,
        access_token=payload.access_token,
        refresh_token=payload.refresh_token,
        expires_at=expires_at
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=['id'],
        set_={
            'access_token': payload.access_token,
            'refresh_token': payload.refresh_token,
            'expires_at': expires_at
        }
    )

    await db.execute(stmt)
    await db.commit()  # Await the commit

    return {"message": "Spotify tokens stored successfully"}