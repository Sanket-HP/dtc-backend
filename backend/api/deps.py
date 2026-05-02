"""Shared FastAPI dependencies – Firebase authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from firebase_admin import auth

from ..firebase_config import db


_bearer = HTTPBearer()


# ─────────────────────────────────────────────
# Return full user object from Firestore
# ─────────────────────────────────────────────
async def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_bearer)
):

    try:
        # Verify Firebase token
        decoded_token = auth.verify_id_token(creds.credentials)

        user_id = decoded_token.get("uid")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )

        # Fetch user from Firestore
        doc = db.collection("users").document(user_id).get()

        if not doc.exists:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        user_data = doc.to_dict()
        user_data["id"] = user_id

        return user_data

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )


# ─────────────────────────────────────────────
# Return only user id
# ─────────────────────────────────────────────
async def get_current_user_id(
    user: dict = Depends(get_current_user)
) -> str:

    return user["id"]