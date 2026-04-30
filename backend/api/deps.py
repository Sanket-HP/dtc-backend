"""Shared FastAPI dependencies (current-user extraction, etc.)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.user import User
from ..utils.auth import decode_access_token


_bearer = HTTPBearer()


# ─────────────────────────────────────────────
# Return full user object
# ─────────────────────────────────────────────
async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:

    payload = decode_access_token(creds.credentials)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id: str | None = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = await db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


# ─────────────────────────────────────────────
# Return only user id (used in /auth/me)
# ─────────────────────────────────────────────
async def get_current_user_id(
    user: User = Depends(get_current_user)
) -> str:

    return user.id